SHELL := /bin/bash
.PHONY: all build run clean help

include .env
export

all: help

help:
	@echo "Usage:"
	@echo "  make build                   - Build the docker image"
	@echo "  make run                     - Run the docker container"
	@echo "  make clean                   - Clean the docker image"

IMAGE_NAME = CHANGE_ME_agent_image_name
CONTAINER_NAME = CHANGE_ME_agent_container_name

build:
	docker build -t $(IMAGE_NAME) .

run:
	docker rm -f $(CONTAINER_NAME) || true
	docker run --name $(CONTAINER_NAME) --env-file .env -p $(PORT):$(PORT) -v $(shell pwd)/agent:/agent/agent $(IMAGE_NAME)

clean:
	docker rm -f $(CONTAINER_NAME) || true
	docker rmi -f $(IMAGE_NAME)|| true
