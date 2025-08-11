# ----------------------------------
# General Targets
# ----------------------------------



# ----------------------------------
# GO BUILD TARGETS
# ----------------------------------
.PHONY: build run

build:
	go build -o bin/orchestrator ./cmd/orchestrator

run:
	go run ./cmd/orchestrator

# ----------------------------------
# PYTHON BUILD TARGETS
# ----------------------------------

.PHONY: build-asr build-tts clean-asr clean-tts

ASR_DIR := services/asr
ASR_VENV := $(ASR_DIR)/.venv
ASR_PY := $(ASR_VENV)/bin/python

build-asr:
	@test -x "$(ASR_PY)" || python3 -m venv $(ASR_VENV)
	$(ASR_PY) -m pip install -U pip
	$(ASR_PY) -m pip install -r $(ASR_DIR)/requirements.txt

build-asr-dev: build-asr
	$(ASR_PY) -m pip install -r $(ASR_DIR)/requirements-dev.txt

build-tts:
	@test -x "$(TTS_PY)" || python3 -m venv $(TTS_VENV)
	$(TTS_PY) -m pip install -U pip
	$(TTS_PY) -m pip install -r $(TTS_DIR)/requirements.txt

build-tts-dev: build-tts
	$(TTS_PY) -m pip install -r $(TTS_DIR)/requirements-dev.txt

clean-asr:
	rm -rf $(ASR_VENV)

clean-tts:
	rm -rf $(TTS_VENV)

# ----------------------------------
# BUF GENERATE TARGETS
# ----------------------------------

# ---- config ----
# venv for codegen tools
VENV_DIR        := .venv/proto
PYTHON          := $(VENV_DIR)/bin/python
PIP             := $(PYTHON) -m pip

# proto files
PROTO_DIR       := api/proto
OUT_DIR         := api/gen
PROTOS          := $(shell find $(PROTO_DIR) -name '*.proto')
GOOGLEAPIS_DIR  := third_party/googleapis

.PHONY: proto-gen proto-venv gen-py gen-go clean clean-venv

proto-gen: clean-gen gen-py gen-go

proto-venv:
	@mkdir -p $(VENV_DIR)
	@test -x "$(PYTHON)" || python3 -m venv $(VENV_DIR)
	$(PIP) install -U pip setuptools wheel
	$(PIP) install -U grpcio-tools mypy-protobuf protobuf

gen-py: proto-venv
	@mkdir -p $(OUT_DIR)
	$(PYTHON) -m grpc_tools.protoc \
		-I $(PROTO_DIR) -I $(GOOGLEAPIS_DIR) \
		--python_out=$(OUT_DIR) \
		--grpc_python_out=$(OUT_DIR) \
		--plugin=protoc-gen-mypy=$(VENV_DIR)/bin/protoc-gen-mypy \
		--mypy_out=$(OUT_DIR) \
		$(PROTOS)

gen-go:
	@mkdir -p $(OUT_DIR)
	protoc -I $(PROTO_DIR) -I $(GOOGLEAPIS_DIR) \
		--go_out=$(OUT_DIR) --go_opt=paths=source_relative \
		--go-grpc_out=$(OUT_DIR) --go-grpc_opt=paths=source_relative \
		$(PROTOS)


# ----------------------------------
# CLEAN TARGETS
# ----------------------------------

clean-gen:
	rm -rf $(OUT_DIR)/*

clean-venv:
	rm -rf $(VENV_DIR)

clean: clean-gen clean-venv
