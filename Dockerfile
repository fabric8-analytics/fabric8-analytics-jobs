FROM registry.centos.org/centos/centos:7
MAINTAINER Fridolin Pokorny <fridolin@redhat.com>

RUN useradd coreapi
COPY ./ /tmp/jobs_install/

RUN yum install -y epel-release && \
    yum install -y python34-devel python34-pip postgresql-devel gcc git && \
    yum clean all

ENV CUCOSLIB_VERSION=64484b0

RUN pushd /tmp/jobs_install &&\
  pip3 install . &&\
  pip3 install git+https://github.com/fabric8-analytics/fabric8-analytics-worker.git@${CUCOSLIB_VERSION} &&\
  popd &&\
  rm -rf /tmp/jobs_install

# A temporary hack to keep Selinon up2date
COPY hack/update_selinon.sh /tmp/
RUN sh /tmp/update_selinon.sh

COPY hack/run_jobs.sh /usr/bin/
COPY bayesian-jobs.py /usr/bin/

USER coreapi
CMD ["/usr/bin/run_jobs.sh"]
