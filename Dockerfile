FROM docker-registry.usersys.redhat.com/bayesian/cucos-worker
MAINTAINER Fridolin Pokorny <fridolin@redhat.com>

RUN useradd coreapi
COPY ./ /tmp/jobs_install/
RUN pushd /tmp/jobs_install &&\
  pip3 install . &&\
  popd &&\
  rm -rf /tmp/jobs_install &&\
  pip3 install git+https://github.com/baytemp/worker.git

# A temporary hack to keep Selinon up2date
COPY hack/update_selinon.sh /tmp/
RUN sh /tmp/update_selinon.sh

COPY hack/run_jobs.sh /usr/bin/
COPY bayesian-jobs.py /usr/bin/

USER coreapi
CMD ["/usr/bin/run_jobs.sh"]
