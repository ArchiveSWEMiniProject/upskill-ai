#!/usr/bin/env python3
"""Resolve ci/jenkins/plugins.txt into ci/jenkins/plugins.lock.

plugins.txt lists the plugins we choose (name:version) and the Jenkins core
version. This script adds every required dependency, picking the newest
version whose required core is not newer than ours (what jenkins-plugin-cli
does by default), and records each plugin's Maven group and SHA-256.

It reads only plain download mirrors and the plugins' own manifests, never
updates.jenkins.io, so it works while that service is down. The image build
(install-plugins.sh) then installs exactly the locked files.

Usage: ci/jenkins/lock-plugins.py [--cache DIR]
"""

import argparse
import hashlib
import io
import re
import sys
import time
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIRRORS = [
    "https://ftp-chi.osuosl.org/pub/jenkins/plugins",
    "https://archives.jenkins.io/plugins",
    "https://mirrors.tuna.tsinghua.edu.cn/jenkins/plugins",
    "https://get.jenkins.io/plugins",
]


def version_key(version: str) -> list:
    """Order Jenkins plugin versions: numeric parts numerically, the rest as text."""
    key = []
    for part in re.split(r"[.\-_]", version):
        key.append((1, int(part), "") if part.isdigit() else (0, 0, part))
    return key


def newer_or_equal(a: str, b: str) -> bool:
    return version_key(a) >= version_key(b)


def fetch(path: str, timeout: int = 60, rounds: int = 3) -> bytes:
    """Try each mirror in turn; repeat the whole round a few times so a short
    network drop does not abort a long resolution."""
    errors = []
    for attempt in range(rounds):
        for mirror in MIRRORS:
            url = f"{mirror}/{path}"
            try:
                with urllib.request.urlopen(url, timeout=timeout) as response:
                    return response.read()
            except OSError as error:
                errors.append(f"{url}: {error}")
        time.sleep(5 * (attempt + 1))
    raise RuntimeError("all mirrors failed:\n  " + "\n  ".join(errors[-len(MIRRORS):]))


def available_versions(name: str) -> list[str]:
    listing = fetch(f"{name}/", timeout=30).decode("utf-8", "replace")
    versions = {
        href for href in re.findall(r'href="([^"/?]+)/"', listing) if href not in {"latest", ".."}
    }
    return sorted(versions, key=version_key, reverse=True)


class Plugin:
    def __init__(self, name: str, version: str, data: bytes):
        self.name, self.version, self.data = name, version, data
        manifest = zipfile.ZipFile(io.BytesIO(data)).read("META-INF/MANIFEST.MF")
        # Manifest lines are wrapped at 72 bytes with a leading space on continuations.
        text = manifest.decode("utf-8").replace("\r\n", "\n").replace("\n ", "")
        fields = dict(line.split(": ", 1) for line in text.splitlines() if ": " in line)
        self.group = fields.get("Group-Id", "org.jenkins-ci.plugins")
        self.core = fields.get("Jenkins-Version") or fields.get("Hudson-Version", "0")
        self.required: dict[str, str] = {}
        self.optional: dict[str, str] = {}
        for entry in filter(None, fields.get("Plugin-Dependencies", "").split(",")):
            spec, _, flags = entry.partition(";")
            dep_name, dep_version = spec.split(":", 1)
            target = self.optional if "resolution:=optional" in flags else self.required
            target[dep_name] = dep_version

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


class Resolver:
    def __init__(self, core: str, cache: Path):
        self.core, self.cache = core, cache
        self.selected: dict[str, Plugin] = {}

    def load(self, name: str, version: str) -> Plugin:
        cached = self.cache / name / version / f"{name}.hpi"
        if not cached.exists():
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(fetch(f"{name}/{version}/{name}.hpi"))
        return Plugin(name, version, cached.read_bytes())

    def newest_compatible(self, name: str, at_least: str) -> Plugin:
        for version in available_versions(name):
            if not newer_or_equal(version, at_least):
                break
            plugin = self.load(name, version)
            if newer_or_equal(self.core, plugin.core):
                return plugin
        raise RuntimeError(f"no version of {name} >= {at_least} supports Jenkins {self.core}")

    def require(self, name: str, at_least: str, pinned: bool = False) -> None:
        current = self.selected.get(name)
        if current and newer_or_equal(current.version, at_least):
            return
        plugin = self.load(name, at_least) if pinned else self.newest_compatible(name, at_least)
        if not newer_or_equal(self.core, plugin.core):
            raise RuntimeError(f"{name} {plugin.version} needs Jenkins {plugin.core}")
        if current:
            print(f"  raising {name} {current.version} -> {plugin.version}", file=sys.stderr)
        self.selected[name] = plugin
        for dep_name, dep_version in plugin.required.items():
            self.require(dep_name, dep_version)

    def check_optional(self) -> None:
        """An optional dependency that is installed anyway must meet its minimum."""
        changed = True
        while changed:
            changed = False
            for plugin in list(self.selected.values()):
                for dep_name, dep_version in plugin.optional.items():
                    current = self.selected.get(dep_name)
                    if current and not newer_or_equal(current.version, dep_version):
                        self.require(dep_name, dep_version)
                        changed = True


def read_spec(path: Path) -> tuple[str, list[tuple[str, str]]]:
    core, plugins = None, []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        match = re.match(r"#\s*jenkins-core:\s*(\S+)", line)
        if match:
            core = match.group(1)
        line = line.split("#", 1)[0].strip()
        if line:
            name, version = line.split(":", 1)
            plugins.append((name, version))
    if not core:
        raise SystemExit(f"{path}: missing '# jenkins-core: <version>' line")
    return core, plugins


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "upskill-plugins")
    args = parser.parse_args()

    core, wanted = read_spec(HERE / "plugins.txt")
    resolver = Resolver(core, args.cache)
    for name, version in wanted:
        print(f"resolving {name}:{version}", file=sys.stderr)
        resolver.require(name, version, pinned=True)
    resolver.check_optional()

    lines = [
        "# Generated by ci/jenkins/lock-plugins.py from plugins.txt; do not edit by hand.",
        f"# jenkins-core: {core}",
        f"# generated: {date.today().isoformat()}",
        "# name:version group sha256",
    ]
    for plugin in sorted(resolver.selected.values(), key=lambda p: p.name):
        lines.append(f"{plugin.name}:{plugin.version} {plugin.group} {plugin.sha256}")
    (HERE / "plugins.lock").write_text("\n".join(lines) + "\n")
    print(f"wrote {len(resolver.selected)} plugins to plugins.lock", file=sys.stderr)


if __name__ == "__main__":
    main()
