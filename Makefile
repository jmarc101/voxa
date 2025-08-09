# ----------------------------------
# General Targets
# ----------------------------------

.PHONY: build run


# ----------------------------------
# GO BUILD TARGETS
# ----------------------------------

build:
	go build -o bin/orchestrator ./cmd/orchestrator

run:
	go run ./cmd/orchestrator
