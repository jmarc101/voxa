# Streaming ASR → TTS & LLM Integration (Cheat Sheet)

## 1) Full‑Replace Partials (Rolling Window)

**Protocol:** send `{utterance_id, rev, text, is_final}`; the client **replaces** the text for that utterance on each update (never concatenate).

**State**
- `rolling` — ring buffer of last `WINDOW_SEC` audio (e.g., 3–5 s)
- `utter` — full utterance buffer (cleared on each START/END)
- `next_partial_at` — time for next partial decode (e.g., now + 300 ms)
- `last_emit` — last emitted string (for debouncing)
- `in_utterance` — inside an utterance (from client/server VAD)

**Loop**
- On START(uid):
  - `utter.clear(); rolling.clear(); in_utterance = True`
  - push pre‑roll into both buffers
- On each CHUNK (20 ms PCM):
  - append to `utter` and `rolling` (drop old samples beyond window)
  - if `now >= next_partial_at` and `in_utterance`:
    - `audio = last WINDOW_SEC from rolling (or all if less)`
    - `hyp = Whisper(audio) → string`
    - if `hyp` non‑empty and `hyp != last_emit`:
      - `emit(utterance_id=uid, text=hyp, is_final=False)`
      - `last_emit = hyp`
    - `next_partial_at = now + PARTIAL_INTERVAL` (e.g., 300 ms)
- On END(uid) (or server VAD end):
  - (optional) add post‑roll to `utter`
  - `final = Whisper(utter) → string` (decode once on full utterance)
  - `emit(utterance_id=uid, text=final, is_final=True)`
  - `in_utterance = False; clear buffers`

**Notes**
- Pre/Post‑roll: 200–500 ms to avoid clipping phonemes.
- Debounce identical partials; rate‑limit emits ≥40 ms.
- Run Whisper off‑loop (`asyncio.to_thread` or process pool).

---

## 2) Stability Filters (When to Act)

Pick one (or combine):

- **n‑1 lag:** process partial `n‑1` only after partial `n` arrives (low latency, simple).
- **Time‑stable:** wait ≥250–300 ms of unchanged text before acting.
- Optional: **LCP over last K partials** to build a stable prefix that only grows.

Client behavior: always **replace** the displayed text per partial; freeze when `is_final=True`.

---

## 3) TTS Policy

- Speak only the **stable part** (n‑1 or time‑stable/LCP), not the volatile tail.
- Start after a meaningful chunk (≈4–6 words or punctuation).
- Synthesize in short phrases so you can **barge‑in**:
  - Stop TTS if mic detects new speech or stable text contradicts what’s being spoken.
  - Re‑synthesize from the updated stable prefix.
- On `is_final=True`: stop preview TTS and speak the committed response.

---

## 4) LLM / Tool Calls

- **High‑stakes actions:** wait for `is_final=True` before executing.
- **Low‑stakes/chat:** you may send the **stable prefix** as a preview; commit on final.
- Example gating:
  - If `is_final`: send full text (commit).
  - Else if `confidence(stable_prefix) ≥ 0.85` and `≥5 words`: send as preview.

---

## 5) Practical Defaults

- Frames: 16 kHz mono PCM16, 20 ms.
- VAD (client preferred): start 100–150 ms voiced; end 300–600 ms silence; aggressiveness 2.
- Rolling window: 3–5 s.
- Partial cadence: 250–400 ms.
- Clear buffers and state after each final.

---

## 6) Flow Summary

1. Receive CHUNK → append to `rolling` and `utter`.
2. On cadence: decode `rolling` → emit full‑replace **partial** (debounced).
3. Agent/TTS/LLM act only on **stable** text (n‑1 or time‑stable).
4. On END: decode `utter` once → emit **final**; stop preview, commit actions.
5. Reset state for next utterance.

