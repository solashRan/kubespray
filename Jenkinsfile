@Library('pipelinex@development') _

properties([
    buildDiscarder(logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '30', numToKeepStr: '1000')),
    [$class: 'ThrottleJobProperty', categories: ['build'], limitOneJobWithMatchingParams: false, maxConcurrentPerNode: 1,
     maxConcurrentTotal: 4, paramsToUseForLimit: '', throttleEnabled: true, throttleOption: 'project']
])


timestamps {
common.notify_slack {
nodes.any_builder_node {
    stage('git clone') {
        deleteDir()
        checkout scm
    }

    stage('build') {
        def image = docker.build("kubespray:${env.BRANCH_NAME}-${env.BUILD_ID}")
    }

    stage('push') {
        def registry = ['https://artifactory.iguazeng.com:6555', 'rans_test', 'iguazio-prod-artifactory-credentials']
        dockerx.images_push([image.id], registry)
    }
}}}
