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
                        sh '.venv/bin/python -m pytest --junitxml=pytest-report.xml --cov=backend --cov-report=xml:coverage.xml --cov-report=html:htmlcov --cov-report=term-missing'
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
