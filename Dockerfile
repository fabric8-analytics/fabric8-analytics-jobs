FROM registry.centos.org/centos/centos:7

ENV LANG=en_US.UTF-8 \
    PV_DIR='/pv' \
    MAVEN_INDEX_CHECKER_PATH='/opt/maven-index-checker' \
    MAVEN_INDEX_CHECKER_DATA_PATH='/pv/index-checker' \
    F8A_WORKER_VERSION=9f5c1c3

RUN useradd coreapi

RUN yum install -y epel-release && \
    yum install -y python34-devel python34-pip postgresql-devel gcc git maven zip unzip && \
    yum clean all

# Install maven-index-checker
COPY hack/install_maven-index-checker.sh /tmp/install_deps/
RUN /tmp/install_deps/install_maven-index-checker.sh

COPY hack/run_jobs.sh /usr/bin/

RUN pip3 install git+https://github.com/fabric8-analytics/fabric8-analytics-worker.git@${F8A_WORKER_VERSION} &&\
    mkdir ${PV_DIR} &&\
    chmod 777 ${PV_DIR}

COPY ./ /tmp/jobs_install/
RUN cd /tmp/jobs_install &&\
    pip3 install . &&\
    rm -rf /tmp/jobs_install

USER coreapi
CMD ["/usr/bin/run_jobs.sh"]
