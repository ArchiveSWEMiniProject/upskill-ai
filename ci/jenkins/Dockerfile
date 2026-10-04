FROM jenkins/jenkins:lts-jdk21@sha256:a660310e39ade10631f774bacd5219de767dfd08947ea5c32a739b5e5bb382c1

USER root
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update -o APT::Update::Error-Mode=any \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

USER jenkins
RUN jenkins-plugin-cli \
    --plugins workflow-aggregator:608.v67378e9d3db_1 git:5.10.1 \
    github-branch-source:1983.vfa_27ed961853 junit:1432.v3f9a_b_73dd986 \
    sonar:2.19.0 timestamper:1.30
