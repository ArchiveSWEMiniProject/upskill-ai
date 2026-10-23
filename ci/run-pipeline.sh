#!/usr/bin/env bash
# Run this repository's Jenkinsfile on a fresh Jenkins LTS + SonarQube pair and
# exit with the build's result (0 = SUCCESS). Used by GitHub Actions on every
# pull request and push to main, and runnable locally the same way:
#
#   ci/run-pipeline.sh                  # Docker
#   DOCKER=podman ci/run-pipeline.sh    # Podman (Docker stages need DOCKER_SOCK)
#
# Environment (all optional):
#   CI_COMMIT    commit to build (default: HEAD of this checkout)
#   CI_OUT_DIR   where logs and reports are written (default: ./ci-out)
#   DOCKER_SOCK  daemon socket to give Jenkins for the Docker stages
#                (default: /var/run/docker.sock if it exists)
#   CI_KEEP=1    leave the containers running afterwards for inspection
set -euo pipefail

DOCKER="${DOCKER:-docker}"
REPO_DIR="$(git rev-parse --show-toplevel)"
COMMIT="${CI_COMMIT:-$(git -C "$REPO_DIR" rev-parse HEAD)}"
OUT="${CI_OUT_DIR:-$REPO_DIR/ci-out}"
RUN_ID="upskill-ci-$$"
NET="$RUN_ID-net"
SONAR_NAME="$RUN_ID-sonarqube"
JENKINS_NAME="$RUN_ID-jenkins"
JENKINS_IMAGE="upskill-ci-jenkins:local"
# Single source of truth for the SonarQube version: the local CI stack.
SONAR_IMAGE="$(sed -n 's/^ *image: *\(.*sonarqube.*\)$/\1/p' "$REPO_DIR/ci/compose.yml" | head -n 1)"
SOCK="${DOCKER_SOCK:-/var/run/docker.sock}"

log() { printf '\n==> %s\n' "$*"; }
random_secret() { head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32; }

SRC_DIR="$(mktemp -d)"
cleanup() {
    rm -rf "$SRC_DIR"
    if [ "${CI_KEEP:-0}" = "1" ]; then
        log "CI_KEEP=1: leaving $JENKINS_NAME and $SONAR_NAME running"
        return
    fi
    "$DOCKER" rm -f "$JENKINS_NAME" "$SONAR_NAME" > /dev/null 2>&1 || true
    "$DOCKER" network rm "$NET" > /dev/null 2>&1 || true
}
trap cleanup EXIT

mkdir -p "$OUT"
[ -n "$SONAR_IMAGE" ] || { echo "Could not read the SonarQube image from ci/compose.yml" >&2; exit 2; }
log "Building commit $COMMIT"

log "Starting SonarQube ($SONAR_IMAGE)"
"$DOCKER" network create "$NET" > /dev/null
# allow_mmap=false avoids needing vm.max_map_count=262144 on the host.
"$DOCKER" run -d --name "$SONAR_NAME" --network "$NET" --network-alias sonarqube \
    -p 127.0.0.1::9000 \
    -e SONAR_SEARCH_JAVAADDITIONALOPTS="-Dnode.store.allow_mmap=false" \
    "$SONAR_IMAGE" > /dev/null

log "Building the Jenkins image (ci/jenkins) while SonarQube starts"
"$DOCKER" build -q -t "$JENKINS_IMAGE" "$REPO_DIR/ci/jenkins" > /dev/null

SONAR_URL="http://$("$DOCKER" port "$SONAR_NAME" 9000/tcp | head -n 1 | sed 's/0\.0\.0\.0/127.0.0.1/')"
log "Waiting for SonarQube at $SONAR_URL"
for _ in $(seq 1 120); do
    curl -fs "$SONAR_URL/api/system/status" 2> /dev/null | grep -q '"status":"UP"' && break
    sleep 5
done
curl -fs "$SONAR_URL/api/system/status" | grep -q '"status":"UP"' \
    || { echo "SonarQube did not come up" >&2; "$DOCKER" logs --tail 50 "$SONAR_NAME" >&2; exit 1; }

SONAR_PASSWORD="$(random_secret)A1!"
curl -fs -u admin:admin -X POST "$SONAR_URL/api/users/change_password" \
    --data-urlencode login=admin --data-urlencode previousPassword=admin \
    --data-urlencode "password=$SONAR_PASSWORD"
sonar_api() { curl -fsS -u "admin:$SONAR_PASSWORD" -X POST "$SONAR_URL/api/$1" "${@:2}"; }

SONAR_TOKEN="$(sonar_api user_tokens/generate --data-urlencode name=jenkins \
    --data-urlencode type=GLOBAL_ANALYSIS_TOKEN \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["token"])')"

# A fresh server has no "new code" history, so the built-in gate (which only
# checks new code) would always pass. This gate checks overall code instead.
# Thresholds are a team decision; see docs/CI.md.
log "Configuring the 'UpSkill CI' quality gate"
sonar_api qualitygates/create --data-urlencode "name=UpSkill CI" > /dev/null
for condition in "coverage LT 60" "reliability_rating GT 1" "security_rating GT 1" "sqale_rating GT 1"; do
    read -r metric op threshold <<< "$condition"
    sonar_api qualitygates/create_condition --data-urlencode "gateName=UpSkill CI" \
        --data-urlencode "metric=$metric" --data-urlencode "op=$op" \
        --data-urlencode "error=$threshold" > /dev/null
done
sonar_api qualitygates/set_as_default --data-urlencode "name=UpSkill CI"

# Give Jenkins only the commit under test, in a throwaway bare repository.
# Nothing from the working tree leaks in, and the mount can be relabelled
# for SELinux (:z) without touching the real checkout.
git init -q --bare "$SRC_DIR/repo.git"
git -C "$REPO_DIR" push -q "$SRC_DIR/repo.git" "$COMMIT:refs/heads/ci-build"
chmod -R a+rX "$SRC_DIR"

log "Starting Jenkins"
CI_ADMIN_PASSWORD="$(random_secret)"
docker_args=()
if [ -S "$SOCK" ]; then
    docker_args=(-v "$SOCK:/var/run/docker.sock" --group-add "$(stat -c %g "$SOCK")")
    echo "Docker stages enabled (socket $SOCK)"
else
    echo "No Docker socket at $SOCK; the Docker stages will be skipped"
fi
"$DOCKER" run -d --name "$JENKINS_NAME" --network "$NET" --network-alias jenkins \
    -p 127.0.0.1::8080 \
    -v "$SRC_DIR/repo.git:/src:ro,z" \
    "${docker_args[@]}" \
    -e CASC_JENKINS_CONFIG=/usr/share/jenkins/casc/casc.yaml \
    -e JAVA_OPTS="-Djenkins.install.runSetupWizard=false -Dhudson.plugins.git.GitSCM.ALLOW_LOCAL_CHECKOUT=true" \
    -e CI_ADMIN_USER=ci -e CI_ADMIN_PASSWORD="$CI_ADMIN_PASSWORD" \
    -e SONAR_HOST_URL=http://sonarqube:9000 -e SONAR_TOKEN="$SONAR_TOKEN" \
    -e CI_COMMIT="$COMMIT" \
    -e CI_DOCKER_NETWORK="$NET" \
    "$JENKINS_IMAGE" > /dev/null

JENKINS_URL="http://$("$DOCKER" port "$JENKINS_NAME" 8080/tcp | head -n 1 | sed 's/0\.0\.0\.0/127.0.0.1/')"
COOKIES="$(mktemp)"
jenkins_get() { curl -fsS -u "ci:$CI_ADMIN_PASSWORD" -b "$COOKIES" -c "$COOKIES" "$JENKINS_URL/$1"; }

log "Waiting for Jenkins at $JENKINS_URL to load its configuration"
for _ in $(seq 1 90); do
    jenkins_get "job/upskill-ai/api/json" > /dev/null 2>&1 && break
    sleep 4
done
jenkins_get "job/upskill-ai/api/json" > /dev/null \
    || { echo "Jenkins did not create the job" >&2; "$DOCKER" logs --tail 80 "$JENKINS_NAME" >&2; exit 1; }

CRUMB="$(jenkins_get crumbIssuer/api/json \
    | python3 -c 'import json, sys; d = json.load(sys.stdin); print(d["crumbRequestField"] + ":" + d["crumb"])')"
curl -fsS -u "ci:$CI_ADMIN_PASSWORD" -b "$COOKIES" -c "$COOKIES" -H "$CRUMB" -X POST \
    "$JENKINS_URL/job/upskill-ai/build" > /dev/null

log "Pipeline output"
until jenkins_get "job/upskill-ai/1/api/json" > /dev/null 2>&1; do sleep 2; done
offset=0
while :; do
    headers="$(mktemp)"
    curl -fsS -u "ci:$CI_ADMIN_PASSWORD" -b "$COOKIES" -D "$headers" \
        "$JENKINS_URL/job/upskill-ai/1/logText/progressiveText?start=$offset" \
        | sed -E $'s/\x1b\\[8mha:[^\x1b]*\x1b\\[0m//g'
    offset="$(sed -n 's/^[Xx]-[Tt]ext-[Ss]ize: *\([0-9]*\).*/\1/p' "$headers")"
    more="$(grep -ci '^x-more-data: *true' "$headers" || true)"
    rm -f "$headers"
    [ "$more" = "0" ] && break
    sleep 3
done

RESULT="$(jenkins_get "job/upskill-ai/1/api/json" \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["result"])')"

log "Collecting reports into $OUT"
jenkins_get "job/upskill-ai/1/consoleText" \
    | sed -E $'s/\x1b\\[8mha:[^\x1b]*\x1b\\[0m//g' > "$OUT/jenkins-console.log" || true
jenkins_get "job/upskill-ai/1/artifact/*zip*/archive.zip" > "$OUT/jenkins-artifacts.zip" 2> /dev/null \
    || rm -f "$OUT/jenkins-artifacts.zip"
curl -fsS -u "admin:$SONAR_PASSWORD" \
    "$SONAR_URL/api/qualitygates/project_status?projectKey=upskill-ai" > "$OUT/sonar-quality-gate.json" || true
curl -fsS -u "admin:$SONAR_PASSWORD" \
    "$SONAR_URL/api/measures/component?component=upskill-ai&metricKeys=coverage,bugs,vulnerabilities,code_smells,ncloc,reliability_rating,security_rating,sqale_rating" \
    > "$OUT/sonar-measures.json" || true
curl -fsS -u "admin:$SONAR_PASSWORD" \
    "$SONAR_URL/api/issues/search?componentKeys=upskill-ai&ps=100" > "$OUT/sonar-issues.json" || true
rm -f "$COOKIES"

log "Jenkins build result: $RESULT"
[ "$RESULT" = "SUCCESS" ]
