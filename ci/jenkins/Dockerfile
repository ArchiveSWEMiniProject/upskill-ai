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
RUN jenkins-plugin-cli \
    --plugins workflow-aggregator:608.v67378e9d3db_1 git:5.10.1 \
    github-branch-source:1983.vfa_27ed961853 junit:1432.v3f9a_b_73dd986 \
    sonar:2.19.0 timestamper:1.30 \
    configuration-as-code:2136.veb_3a_554550b_f job-dsl:3732.v9a_c49a_61a_313 \
    plain-credentials:199.v9f8e1f741799

# Configuration as code for the ephemeral CI server: SonarQube connection,
# scanner tool and the pipeline job. Applied only when CASC_JENKINS_CONFIG
# points here (ci/run-pipeline.sh sets it); the long-running local server in
# ci/compose.yml keeps its manual setup.
COPY --chown=jenkins:jenkins casc.yaml /usr/share/jenkins/casc/casc.yaml
