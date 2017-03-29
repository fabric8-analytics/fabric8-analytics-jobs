#!/usr/bin/env groovy

node('docker') {

    def image = docker.image('bayesian/coreapi-jobs')

    stage('Checkout') {
        checkout scm
    }

    stage('Build') {
        dockerCleanup()
        // hack
        dir('worker') {
            git url: 'https://github.com/baytemp/worker.git', branch: 'master', credentialsId: 'baytemp-ci-gh'
        }
        docker.build(image.id, '--pull --no-cache .')
    }

    stage('Tests') {
        timeout(30) {
            echo 'No tests!'
        }
    }

    stage('Integration Tests') {
        ws {
            sh "docker tag ${image.id} docker-registry.usersys.redhat.com/${image.id}"
            docker.withRegistry('https://docker-registry.usersys.redhat.com/') {
                docker.image('bayesian/bayesian-api').pull()
                docker.image('bayesian/cucos-worker').pull()
                docker.image('bayesian/coreapi-downstream-data-import').pull()
                docker.image('bayesian/coreapi-pgbouncer').pull()
            }

            git url: 'https://github.com/baytemp/common.git', branch: 'master', credentialsId: 'baytemp-ci-gh'
            dir('integration-tests') {
                timeout(30) {
                    sh './runtest.sh'
                }
            }
        }
    }

    if (env.BRANCH_NAME == 'master') {
        stage('Push Images') {
            def commitId = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
            docker.withRegistry('https://docker-registry.usersys.redhat.com/') {
                image.push('latest')
                image.push(commitId)
            }
            docker.withRegistry('https://registry.devshift.net/') {
                image.push('latest')
                image.push(commitId)
            }
        }
    }
}

if (env.BRANCH_NAME == 'master') {
    node('oc') {
        stage('Deploy - dev') {
            sh 'oc --context=dev deploy bayesian-jobs --latest'
        }

        stage('Deploy - rh-idev') {
            sh 'oc --context=rh-idev deploy bayesian-jobs --latest'
        }

        stage('Deploy - dsaas') {
            sh 'oc --context=dsaas deploy bayesian-jobs --latest'
        }
    }
}
