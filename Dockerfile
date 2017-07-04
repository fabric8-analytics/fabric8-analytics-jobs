FROM registry.centos.org/centos/centos:7
MAINTAINER Fridolin Pokorny <fridolin@redhat.com>

ENV LANG=en_US.UTF-8 \
    MAVEN_INDEX_CHECKER_PATH='/opt/maven-index-checker' \
    F8A_WORKER_VERSION=5de9551f

RUN useradd coreapi

RUN yum install -y epel-release && \
    yum install -y python34-devel python34-pip postgresql-devel gcc git maven zip unzip && \
    yum clean all

# Install maven-index-checker
COPY hack/install_maven-index-checker.sh /tmp/install_deps/
RUN /tmp/install_deps/install_maven-index-checker.sh

COPY ./ /tmp/jobs_install/
RUN pushd /tmp/jobs_install &&\
  pip3 install . &&\
  pip3 install git+https://github.com/fabric8-analytics/fabric8-analytics-worker.git@${F8A_WORKER_VERSION} &&\
  popd &&\
  rm -rf /tmp/jobs_install

# A temporary hack to keep Selinon up2date
COPY hack/update_selinon.sh /tmp/
RUN sh /tmp/update_selinon.sh

COPY hack/run_jobs.sh /usr/bin/
COPY f8a-jobs.py /usr/bin/

USER coreapi
CMD ["/usr/bin/run_jobs.sh"]
