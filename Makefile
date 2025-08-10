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


# ----------------------------------
# PYTHON BUILD TARGETS
# ----------------------------------

.PHONY: build-asr build-tts

build-asr:
	cd services/asr && \
	python3 -m venv .venv && \
	source .venv/bin/activate && \
	pip install --upgrade pip && \
	pip install -r requirements.txt

build-tts:
	cd services/tts && \
	python3 -m venv .venv && \
	source .venv/bin/activate && \
	python -m pip install -r requirements.txt
