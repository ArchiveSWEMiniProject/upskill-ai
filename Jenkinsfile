pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Backend checks') {
            steps {
                sh 'python -m pip install -r requirements-dev.txt'
                sh 'ruff check backend tests'
                sh 'pytest --junitxml=pytest-report.xml --cov=backend --cov-report=xml:coverage.xml --cov-report=html:htmlcov --cov-report=term-missing'
            }
            post { always { junit allowEmptyResults: true, testResults: 'pytest-report.xml' } }
        }

        stage('Frontend checks') {
            steps {
                dir('frontend') {
                    sh 'npm ci'
                    sh 'npm test -- --coverage'
                    sh 'npm run lint'
                    sh 'npm run build'
                }
            }
        }

        stage('SonarQube analysis') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh 'sonar-scanner'
                }
            }
        }

        stage('Quality gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    script {
                        def gate = waitForQualityGate()
                        if (gate.status != 'OK') {
                            error "SonarQube quality gate failed: ${gate.status}"
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'coverage.xml,htmlcov/**,pytest-report.xml,frontend/coverage/**', allowEmptyArchive: true
        }
    }
}
