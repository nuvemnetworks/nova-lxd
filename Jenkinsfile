pipeline {
    agent { dockerfile true }
    stages {
        stage('Build') {
            steps {
                sh 'python setup.py sdist bdist_wheel'
            }
        }

        stage('Upload to Nexus') {
            when {
                branch 'master'
            }
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'nexus_credentials',
                        usernameVariable: 'TWINE_USERNAME',
                        passwordVariable: 'TWINE_PASSWORD'
                    )
                ]) {
                    sh 'twine upload --repository-url http://nexus.dev.pureport.com/repository/pypi-private/ dist/*'
                }
            }
        }
    }
    post {
        always {
            /* clean up our workspace */
            deleteDir()
        }
        success {
            slackSend(color: '#30A452', message: "SUCCESS: <${env.BUILD_URL}|${env.JOB_NAME}#${env.BUILD_NUMBER}>")
        }
        unstable {
            slackSend(color: '#DD9F3D', message: "UNSTABLE: <${env.BUILD_URL}|${env.JOB_NAME}#${env.BUILD_NUMBER}>")
        }
        failure {
            slackSend(color: '#D41519', message: "FAILED: <${env.BUILD_URL}|${env.JOB_NAME}#${env.BUILD_NUMBER}>")
        }
    }
}
