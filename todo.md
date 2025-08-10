## TODO – Steps

### 1. Proto + codegen
- Write `api/proto/asr.proto` and `tts.proto`
- Run `buf generate` → Go + Python stubs land in `api/gen/...`.
- ✅ You can import the generated clients/servers.

---

### 2. Spin up sidecars (stubbed)
- Python **ASR** server that emits fake partials/final.
- Python **TTS** server that just logs text (no audio yet).
- `docker compose up asr tts ollama`
- ✅ Containers listen on `7010/7020`; health endpoints respond.

---

### 3. Orchestrator → ASR streaming (no VAD yet)
- In Go, use `internal/audio/capture.go` to grab 20 ms PCM16 frames.
- Stream to ASR via gRPC; print tokens to stdout.
- For determinism, start by feeding a WAV file instead of mic.
- ✅ You see partials/final coming back quickly.

---

### 4. Swap in real ASR
- Replace fake decoder with **faster-whisper** (or whisper.cpp server).
- Keep streaming interface identical.
- ✅ Sample audio transcribes correctly.

---

### 5. Add VAD + turn state machine
- Use `internal/audio/vad.go` (energy gate) + ring buffer pre-roll.
- Logic: wake (manual hotkey for now) → Listening; silence >800 ms → close ASR stream.
- ✅ Speaking stops the stream; silence ends the turn reliably.

---

### 6. LLM → TTS path
- Call Ollama HTTP on ASR final; stream tokens → send to TTS gRPC.
- For first cut, TTS server can return WAV/PCM; orchestrator plays it (CoreAudio/ALSA) or just saves a WAV.
- ✅ Assistant “speaks” the reply.

---

### 7. Wake-word + barge-in
- Add Porcupine (or a Python WW sidecar) and replace the manual hotkey.
- Implement TTS duck/stop on wake word if you want barge-in.
- ✅ “Hey Bot” starts a new turn; speaking over TTS interrupts.

---

### 8. Hardening
- Health checks, reconnects, timeouts, bounded queues, logs/metrics.
- Buildx multi-arch images; keep orchestrator native on macOS at first (mic in Docker is pain).
