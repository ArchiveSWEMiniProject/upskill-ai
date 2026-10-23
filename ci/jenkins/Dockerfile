FROM docker.io/jenkins/jenkins:lts-jdk21@sha256:a660310e39ade10631f774bacd5219de767dfd08947ea5c32a739b5e5bb382c1

# uv supplies the CPython 3.12 that the stack targets (the Debian base only ships 3.13).
COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /usr/local/bin/uv
# Docker CLI and compose plugin for the image build and deploy smoke-test stages.
# They talk to the host daemon through a mounted socket; no daemon runs in here.
COPY --from=docker.io/library/docker:28.5.2-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker.io/library/docker:28.5.2-cli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/libexec/docker/cli-plugins/docker-compose
# SonarScanner CLI 8.1 (runs on the image's Java 21). Preinstalled so a fresh
# server does not depend on downloading tool metadata on first use.
COPY --from=docker.io/sonarsource/sonar-scanner-cli:12.2.0.4256_8.1.0 /opt/sonar-scanner /opt/sonar-scanner

USER root
# Install the interpreter outside /var/jenkins_home, which is a volume and
# would hide anything installed there at image build time.
ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python \
    UV_PYTHON_PREFERENCE=only-managed
RUN uv python install 3.12 \
    && chown -R jenkins:jenkins /opt/uv \
    # CI mounts a checkout owned by another uid; let git read it.
    && git config --system --add safe.directory '*'

USER jenkins
# Exact plugin set from plugins.lock (regenerate with lock-plugins.py), each
# file checked against its SHA-256. Installing from the lock instead of with
# jenkins-plugin-cli means the build never needs updates.jenkins.io, whose
# outages otherwise break every CI run.
COPY --chown=jenkins:jenkins plugins.lock install-plugins.sh /usr/share/jenkins/
RUN /usr/share/jenkins/install-plugins.sh /usr/share/jenkins/plugins.lock /usr/share/jenkins/ref/plugins

# Configuration as code for the ephemeral CI server: SonarQube connection,
# scanner tool and the pipeline job. Applied only when CASC_JENKINS_CONFIG
# points here (ci/run-pipeline.sh sets it); the long-running local server in
# ci/compose.yml keeps its manual setup.
COPY --chown=jenkins:jenkins casc.yaml /usr/share/jenkins/casc/casc.yaml
