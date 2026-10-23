pipeline {
    agent any
    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
    }
    stages {
        stage('Checkout') { steps { checkout scm } }
        stage('Backend checks') {
            steps {
                script {
                    // Fresh 3.12 venv every build, matching the stack and the API image.
                    sh 'uv venv --clear --python 3.12 .venv'
                    sh '.venv/bin/python -c "import sys; assert sys.version_info[:2] == (3, 12), sys.version"'
                    sh 'uv pip install --python .venv/bin/python -r requirements-dev.txt'
                    if (fileExists('requirements.txt')) {
                        sh 'uv pip install --python .venv/bin/python -r requirements.txt'
                    }
                    if (fileExists('backend')) {
                        sh '.venv/bin/python -m ruff check backend'
                        // Database tests get a throwaway Postgres when Docker is available;
                        // without one they are skipped (and the log says so).
                        def testDb = startTestDatabase()
                        try {
                            withEnv(testDb ? ["TEST_DATABASE_URL=${testDb}"] : []) {
                                sh '.venv/bin/python -m pytest --junitxml=pytest-report.xml --cov=backend --cov-report=xml:coverage.xml --cov-report=html:htmlcov --cov-report=term-missing'
                            }
                        } finally {
                            stopTestDatabase()
                        }
                    } else { error 'Backend directory is missing; backend checks cannot run.' }
                }
            }
            post { always { junit allowEmptyResults: true, testResults: 'pytest-report.xml' } }
        }
        stage('SonarQube analysis') {
            steps {
                script {
                    def scannerHome = tool 'SonarScanner'
                    withSonarQubeEnv('SonarQube') {
                        sh "\"${scannerHome}/bin/sonar-scanner\""
                    }
                }
            }
        }
        stage('Quality gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    // Wait for SonarQube's background task here, so the gate does not
                    // depend on SonarQube being able to call this Jenkins back
                    // (newer SonarQube refuses webhooks to private addresses).
                    withSonarQubeEnv('SonarQube') {
                        sh '''
                            task_url="$(sed -n 's/^ceTaskUrl=//p' .scannerwork/report-task.txt)"
                            until curl -fsS -u "$SONAR_AUTH_TOKEN:" "$task_url" \
                                | grep -q -E '"status":"(SUCCESS|FAILED|CANCELED)"'; do
                                sleep 2
                            done
                        '''
                    }
                    script {
                        def gate = waitForQualityGate()
                        if (gate.status != 'OK') { error "SonarQube quality gate failed: ${gate.status}" }
                    }
                }
            }
        }
        // The two stages below need a Docker daemon (the CI server mounts the
        // host socket). A Jenkins without one skips them and says so.
        stage('Docker build') {
            when { expression { dockerAvailable() } }
            steps {
                sh 'docker build -f backend/Dockerfile -t upskill-api:ci .'
                sh 'docker build -t upskill-web:ci frontend'
            }
        }
        stage('Deploy smoke test') {
            when { expression { dockerAvailable() } }
            environment {
                COMPOSE_PROJECT_NAME = "upskill-ci-${env.BUILD_NUMBER}"
                COMPOSE_FILE = 'docker-compose.yml:ci/compose.smoke.yml'
            }
            steps {
                // Throwaway secrets for this run only; compose refuses to start without them.
                sh '''
                    export POSTGRES_PASSWORD="$(head -c 32 /dev/urandom | base64 | tr -dc A-Za-z0-9)"
                    export JWT_SECRET="$(head -c 48 /dev/urandom | base64 | tr -dc A-Za-z0-9)"
                    docker compose up -d --build --wait --wait-timeout 180
                    docker compose exec -T upskill-api python -c "
import json, time, urllib.request
for attempt in range(30):
    try:
        body = json.load(urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=2))
        break
    except OSError:
        time.sleep(2)
else:
    raise SystemExit('API health endpoint never answered')
assert body == {'status': 'ok'}, body
print('health:', body)
"
                    docker compose exec -T upskill-db pg_isready -U upskill
                    # The API container migrates on start; the schema must be at head.
                    if [ -f alembic.ini ]; then
                        docker compose exec -T upskill-api alembic current 2>&1 | tee alembic-current.txt
                        grep -q '(head)' alembic-current.txt
                    fi
                '''
            }
            post {
                always {
                    sh 'docker compose logs --no-color > compose-smoke.log 2>&1 || true'
                    sh 'docker compose down -v --remove-orphans || true'
                }
            }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'coverage.xml,htmlcov/**,pytest-report.xml,compose-smoke.log', allowEmptyArchive: true
        }
    }
}

def dockerAvailable() {
    def ok = sh(returnStatus: true, script: 'docker info > /dev/null 2>&1') == 0
    if (!ok) { echo 'No Docker daemon reachable from this agent; skipping Docker stages.' }
    return ok
}

def testDatabaseName() { "upskill-test-db-${env.BUILD_NUMBER}" }

// Starts Postgres on the CI server's Docker network (ci/run-pipeline.sh sets
// CI_DOCKER_NETWORK) and returns its URL, or null when that is not possible.
def startTestDatabase() {
    if (!env.CI_DOCKER_NETWORK || !dockerAvailable()) {
        echo 'No CI Docker network; database tests will be skipped.'
        return null
    }
    def password = sh(returnStdout: true,
        script: 'head -c 48 /dev/urandom | base64 | tr -dc A-Za-z0-9 | head -c 24').trim()
    withEnv(["TEST_DB_NAME=${testDatabaseName()}", "TEST_DB_PASSWORD=${password}"]) {
        sh '''
            set +x  # keep the throwaway password out of the console log
            echo "Starting test database $TEST_DB_NAME"
            docker run -d --rm --name "$TEST_DB_NAME" --network "$CI_DOCKER_NETWORK" \
                -e POSTGRES_USER=upskill -e POSTGRES_PASSWORD="$TEST_DB_PASSWORD" \
                -e POSTGRES_DB=upskill_test docker.io/library/postgres:16-alpine > /dev/null
            # TCP only comes up once initialisation has finished.
            for attempt in $(seq 1 60); do
                docker exec "$TEST_DB_NAME" pg_isready -q -h 127.0.0.1 -U upskill -d upskill_test && exit 0
                sleep 1
            done
            echo "Test database did not start" >&2
            exit 1
        '''
    }
    return "postgresql://upskill:${password}@${testDatabaseName()}:5432/upskill_test"
}

def stopTestDatabase() {
    if (env.CI_DOCKER_NETWORK) {
        sh "docker rm -f ${testDatabaseName()} > /dev/null 2>&1 || true"
    }
}
