FROM docker.io/jenkins/jenkins:lts-jdk21@sha256:a660310e39ade10631f774bacd5219de767dfd08947ea5c32a739b5e5bb382c1

# uv supplies the CPython 3.12 that the stack targets (the Debian base only ships 3.13).
COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /usr/local/bin/uv

USER root
# Install the interpreter outside /var/jenkins_home, which is a volume and
# would hide anything installed there at image build time.
ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python \
    UV_PYTHON_PREFERENCE=only-managed
RUN uv python install 3.12 \
    && chown -R jenkins:jenkins /opt/uv

USER jenkins
RUN jenkins-plugin-cli \
    --plugins workflow-aggregator:608.v67378e9d3db_1 git:5.10.1 \
    github-branch-source:1983.vfa_27ed961853 junit:1432.v3f9a_b_73dd986 \
    sonar:2.19.0 timestamper:1.30
