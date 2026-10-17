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
                    script {
                        def gate = waitForQualityGate()
                        if (gate.status != 'OK') { error "SonarQube quality gate failed: ${gate.status}" }
                    }
                }
            }
        }
    }
    post { always { archiveArtifacts artifacts: 'coverage.xml,htmlcov/**,pytest-report.xml', allowEmptyArchive: true } }
}
