─ cmd/
│  └─ orchestrator/             # Go main()
├─ internal/
│  ├─ core/                     # dialog state, routing, VAD gate
│  ├─ clients/                  # gRPC clients (asr, tts), http (ollama)
│  ├─ audio/                    # mic I/O, ring buffers
│  ├─ bus/                      # events (if you keep NATS/Redis)
│  └─ memory/                   # sqlite + sqlite-vec (optional)
├─ api/
│  ├─ proto/                    # *.proto (asr, tts, events, common)
│  └─ gen/                      # generated code (Go + Python)
├─ services/
│  ├─ asr/                      # Python ASR service (faster-whisper or whisper.cpp shim)
│  │  ├─ py/                    # python package
│  │  ├─ models/                # ASR models (mounted volume)
│  │  ├─ server.py              # gRPC server
│  │  ├─ requirements.txt
│  │  └─ Dockerfile
│  ├─ tts/                      # Python Piper/Coqui TTS
│  │  ├─ py/
│  │  ├─ voices/                # voice data (mounted volume)
│  │  ├─ server.py              # gRPC server
│  │  ├─ requirements.txt
│  │  └─ Dockerfile
│  └─ llm/
│     └─ ollama/                # configs/scripts for Ollama container (no code)
├─ configs/
│  ├─ dev.yaml                  # ports, model names, thresholds
│  └─ prod.yaml
├─ deploy/
│  ├─ docker-compose.yml        # local dev orchestration
│  └─ k8s/                      # optional manifests/helm later
├─ scripts/                     # helper scripts (buf, codegen, run)
├─ docs/
│  └─ adr/                      # decisions
├─ .env                         # env vars (ports, model names)
├─ buf.yaml                     # protobuf config
├─ buf.gen.yaml                 # codegen targets
├─ go.mod
├─ Makefile
└─ README.md
