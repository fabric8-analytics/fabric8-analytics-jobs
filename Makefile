ifeq ($(TARGET),rhel)
  DOCKERFILE := Dockerfile.rhel
  REPOSITORY := openshiftio/rhel-bayesian-coreapi-jobs
else
  DOCKERFILE := Dockerfile
  REPOSITORY := openshiftio/bayesian-coreapi-jobs
endif

REGISTRY := quay.io
DEFAULT_TAG=latest
TEST_IMAGE=jobs-tests

.PHONY: all docker-build fast-docker-build test get-image-name get-image-repository

all: fast-docker-build

docker-build:
	docker build --no-cache -t $(REGISTRY)/$(REPOSITORY):$(DEFAULT_TAG) -f $(DOCKERFILE) .
	docker tag $(REGISTRY)/$(REPOSITORY):$(DEFAULT_TAG) $(TEST_IMAGE):$(DEFAULT_TAG)

docker-build-tests: docker-build
	docker build --no-cache -t $(TEST_IMAGE) -f Dockerfile.tests .

fast-docker-build:
	docker build -t $(REGISTRY)/$(REPOSITORY):$(DEFAULT_TAG) -f $(DOCKERFILE) .
	docker tag $(REGISTRY)/$(REPOSITORY):$(DEFAULT_TAG) $(TEST_IMAGE):$(DEFAULT_TAG)

fast-docker-build-tests: fast-docker-build
	docker build -t jobs-tests -f Dockerfile.tests .

test: fast-docker-build-tests
	./runtest.sh

get-image-name:
	@echo $(REGISTRY)/$(REPOSITORY):$(DEFAULT_TAG)

get-image-repository:
	@echo $(REPOSITORY)

get-push-registry:
	@echo $(REGISTRY)
