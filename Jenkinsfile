pipeline {
    agent any

    environment {
        // This will hold the Render Deploy Hook URL later
        RENDER_DEPLOY_HOOK = credentials('render-deploy-hook')
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Pulling the latest secure vault code from GitHub...'
                checkout scm
            }
        }

        stage('Build Environment') {
            steps {
                echo 'Installing Python dependencies...'
                bat 'python -m pip install --upgrade pip'
                bat 'pip install -r requirements.txt'
            }
        }

        stage('Security Audit') {
            steps {
                echo 'Running Bandit security scan on the Python backend...'
                // This scans main.py for exposed keys, bad imports, and vulnerabilities
                bat 'bandit -r main.py -f custom'
            }
        }

        stage('Trigger Cloud Deployment') {
            steps {
                echo 'Security checks passed! Triggering Render cloud deployment...'
                // Pings Render to pull the approved code and go live
                bat "curl -X POST %RENDER_DEPLOY_HOOK%"
            }
        }
    }

    post {
        success {
            echo '✅ Pipeline completed successfully. The vault is live!'
        }
        failure {
            echo '❌ Pipeline failed. Security audit or build encountered an error. Deployment halted.'
        }
    }
}