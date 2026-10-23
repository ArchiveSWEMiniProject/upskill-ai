#!/bin/sh
# Install exactly the plugins in plugins.lock into Jenkins' reference directory.
# Every file must match its locked SHA-256. Sources are tried in order, so the
# build does not depend on any single Jenkins download service being up
# (updates.jenkins.io is not used at all).
#
# Usage: install-plugins.sh <plugins.lock> <target dir>
set -eu

lock="$1"
target="$2"
mkdir -p "$target"

sources() { # name version group -> candidate URLs, one per line
    group_path="$(printf '%s' "$3" | tr . /)"
    echo "https://repo.jenkins-ci.org/releases/$group_path/$1/$2/$1-$2.hpi"
    echo "https://ftp-chi.osuosl.org/pub/jenkins/plugins/$1/$2/$1.hpi"
    echo "https://archives.jenkins.io/plugins/$1/$2/$1.hpi"
    echo "https://mirrors.tuna.tsinghua.edu.cn/jenkins/plugins/$1/$2/$1.hpi"
    echo "https://get.jenkins.io/plugins/$1/$2/$1.hpi"
}

grep -v '^#' "$lock" | while read -r spec group sha; do
    [ -n "$spec" ] || continue
    name="${spec%%:*}"
    version="${spec#*:}"
    file="$target/$name.jpi"
    installed=""
    for url in $(sources "$name" "$version" "$group"); do
        if curl -fsSL --connect-timeout 10 --max-time 120 --retry 2 -o "$file.part" "$url" \
            && echo "$sha  $file.part" | sha256sum -c - > /dev/null 2>&1; then
            mv "$file.part" "$file"
            installed="$url"
            break
        fi
        rm -f "$file.part"
    done
    if [ -z "$installed" ]; then
        echo "FAILED: $name $version (no source had a file matching the locked checksum)" >&2
        exit 1
    fi
    echo "$name $version  <- $(echo "$installed" | cut -d/ -f3)"
done
echo "Installed $(ls "$target" | grep -c '\.jpi$') plugins from $lock"
