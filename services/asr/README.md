# Streaming ASR with Rolling Window Partials (Full-Replace Algorithm)

This document describes a **simple, robust** algorithm for generating **rolling-window partials** and a **final transcript** for each utterance when using Whisper (or similar ASR).

## Overview

We use:
- **Client or server VAD** to detect utterance boundaries (`START`, `CHUNK`, `END`).
- A **rolling window** of recent audio to generate partial hypotheses.
- A **full utterance buffer** to generate the final result.
- **Full-replace** strategy: each partial is a complete hypothesis for the current utterance. The client simply **replaces** the displayed text on each partial.

---

## State Variables

- `rolling` — ring buffer of last `WINDOW_SEC` audio (e.g., 3–5 seconds)
- `utter` — full utterance buffer (cleared on each START/END)
- `next_partial_at` — next time to run a partial decode (e.g., now + 300 ms)
- `last_emit` — last string emitted (for debouncing identical output)
- `in_utterance` — boolean, true if inside an utterance

---

## Loop

### On `START(uid)`:
1. `utter.clear()`
2. `rolling.clear()`
3. `in_utterance = True`
4. Push any **pre-roll audio** into both buffers

---

### On each `CHUNK` (20 ms PCM):
1. Append to `utter`
2. Append to `rolling` (drop old samples beyond window length)
3. If `now >= next_partial_at` **and** `in_utterance`:
   - Extract `audio = last WINDOW_SEC from rolling` (or all if less)
   - Run `hyp = Whisper(audio)` → string
   - If `hyp` is **non-empty** and `hyp != last_emit`:
     - `emit(utterance_id=uid, text=hyp, is_final=False)`
     - `last_emit = hyp`
   - Update `next_partial_at = now + PARTIAL_INTERVAL` (e.g., 300 ms)

---

### On `END(uid)` (or server VAD end):
1. (Optional) Add **post-roll audio** to `utter`
2. Run `final = Whisper(utter)` → string (decode full utterance once)
3. `emit(utterance_id=uid, text=final, is_final=True)`
4. `in_utterance = False`
5. Clear `rolling` and `utter`

---

## Notes

- **Pre/Post-roll**: Include a short amount of audio before START (~200 ms) and after END (~300–500 ms) to avoid cutting phonemes.
- **Debounce**: Skip sending partials that are identical to the last one.
- **Cadence**: `PARTIAL_INTERVAL` of 250–400 ms balances latency and CPU load.
- **Execution**: Run Whisper off the event loop (`asyncio.to_thread` or a small process pool).
- **Client UI**: Replace text for the current `utterance_id` on each partial; freeze it when `is_final=True`.

---

## Example Timeline

With:
- `WINDOW_SEC = 3`
- `PARTIAL_INTERVAL = 0.3s`

| Time  | Rolling Window Audio                      | Emitted Text (Full Hypothesis)                  |
|-------|--------------------------------------------|--------------------------------------------------|
| 0.3s  | "hello"                                    | `"hello"`                                        |
| 0.6s  | "hello this"                               | `"hello this"`                                   |
| 0.9s  | "hello this is"                            | `"hello this is"`                                |
| 3.0s  | "hello this is a test"                     | `"hello this is a test"`                         |
| 6.0s  | "is a test of the emergency broadcast"     | `"is a test of the emergency broadcast"`         |
| END   | **full utterance decode**                  | `"hello this is a test of the emergency broadcast system please remain calm"` (**final**) |

---

## Advantages

- **Simple client**: Just replace text on each update.
- **Accurate final**: Generated from the **full utterance**.
- **Low latency**: Frequent partials keep the UI responsive.
- **Robust to rewrites**: Earlier words can be corrected before final.

---

## Pseudocode

```python
if START(uid):
    utter.clear()
    rolling.clear()
    in_utterance = True
    next_partial_at = now()

if CHUNK(uid, audio):
    if not in_utterance:
        return
    utter.push(audio)
    rolling.push(audio)
    if now() >= next_partial_at:
        hyp = Whisper(rolling.last(WINDOW_SEC))
        if hyp and hyp != last_emit:
            emit(uid, hyp, is_final=False)
            last_emit = hyp
        next_partial_at = now() + PARTIAL_INTERVAL

if END(uid):
    final = Whisper(utter)
    emit(uid, final, is_final=True)
    in_utterance = False
    rolling.clear()
    utter.clear()
    last_emit = ""
```
