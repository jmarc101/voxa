# Voxa

A voice assistant platform.

## Project Structure

```
voxa/
├─ api/
│  ├─ proto/               # *.proto files (asr, tts, events, common)
│  └─ gen/                 # generated code (Go + Python)
├─ assets/
│  └─ audio/               # Audio assets (contains hello_world.wav)
├─ cmd/
│  └─ orchestrator/        # Go main() entrypoint
├─ internal/
│  ├─ audio/               # mic I/O, ring buffers
│  ├─ bus/                 # events system
│  ├─ clients/             # gRPC clients (asr, tts), http (ollama)
│  ├─ core/                # dialog state, routing, VAD gate
│  └─ memory/              # sqlite + sqlite-vec
├─ services/
│  ├─ asr/                 # Python ASR service (faster-whisper or whisper.cpp)
│  ├─ llm/                 # LLM service
│  └─ tts/                 # (Python)Text-to-speech service
```

## Getting Started

*[Add instructions for setting up and running the project]*

## License

See [LICENSE](LICENSE) file for details.
