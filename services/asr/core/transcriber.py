from __future__ import annotations
import asyncio
from dataclasses import dataclass
from enum import Enum, auto
from typing import AsyncIterator, Optional, Protocol, Tuple

import numpy as np

from core.sliding_window import AudioSlidingWindow


class TranscribeEngine(Protocol):
    """Minimal engine interface the Transcriber needs.

    Implementations should accept a float32 array in [-1, 1] (mono) and return
    a text hypothesis for that audio.
    """

    async def transcribe(self, audio_f32: np.ndarray) -> str:  # pragma: no cover - interface only
        ...


class Ev(Enum):
    AUDIO = auto()
    FLUSH = auto()
    END = auto()


@dataclass
class Event:
    kind: Ev
    data: Optional[bytes] = None  # PCM16 LE for AUDIO


def _stitch(prev: str, new: str) -> str:
    """Greedy suffix/prefix overlap stitcher.

    Ensures the running hypothesis grows smoothly (cheap PoC approach).
    Example: prev="turn on the ki", new="the kitchen lights" ->
             "turn on the kitchen lights"
    """
    if not prev:
        return new
    if not new:
        return prev
    max_k = min(len(prev), len(new))
    for k in range(max_k, 0, -1):
        if prev.endswith(new[:k]):
            return prev + new[k:]
    return prev + new


class Transcriber:
    """Streaming transcription helper built around a rolling window.

    Responsibilities
    ----------------
    • Ingest PCM16 frames into an AudioSlidingWindow.
    • Optionally emit PARTIAL hypotheses on a fixed cadence (stride).
    • On FLUSH/END, emit a FINAL hypothesis and reset state.
    • Maintain a running `hypothesis` string (stitched partials).

    Notes
    -----
    • This class is transport-agnostic: feed it events from gRPC, websockets,
      or tests. Your gRPC handler can simply bridge requests → `feed_*()` and
      iterate over `run()` to retrieve ('PARTIAL'|'FINAL', text).
    • For a final-only PoC, set `emit_partials=False`.
    """

    def __init__(
        self,
        engine: TranscribeEngine,
        *,
        sample_rate_hz: int = 16000,
        window_ms: int = 3000,
        tail_ms: int = 2000,
        stride_ms: int = 400,
        emit_partials: bool = False,
    ) -> None:
        self.engine = engine
        self.win = AudioSlidingWindow(window_size_ms=window_ms, sample_rate_hz=sample_rate_hz)
        self.tail_ms = int(tail_ms)
        self.emit_partials = bool(emit_partials)
        self.stride_samples = max(1, (sample_rate_hz * int(stride_ms)) // 1000)
        self._since_emit = 0
        self.hypothesis: str = ""
        self.q: "asyncio.Queue[Event]" = asyncio.Queue(maxsize=1024)

    # ----------------- feeders -----------------
    async def feed_audio(self, pcm16_le: bytes) -> None:
        await self.q.put(Event(Ev.AUDIO, data=pcm16_le))

    async def flush(self) -> None:
        await self.q.put(Event(Ev.FLUSH))

    async def end(self) -> None:
        await self.q.put(Event(Ev.END))

    # ----------------- runner ------------------
    async def run(self) -> AsyncIterator[Tuple[str, str]]:
        """Consume events and yield (kind, text).

        Yields
        ------
        ("PARTIAL", text) or ("FINAL", text)
        """
        while True:
            ev = await self.q.get()

            if ev.kind is Ev.AUDIO and ev.data:
                n = self.win.append(ev.data)
                if self.emit_partials:
                    self._since_emit += n
                    while self._since_emit >= self.stride_samples:
                        self._since_emit -= self.stride_samples
                        tail = self.win.tail_ms(self.tail_ms, as_float=True)
                        text = (await self.engine.transcribe(tail)).strip()
                        if text:
                            self.hypothesis = _stitch(self.hypothesis, text)
                            yield ("PARTIAL", self.hypothesis)
                continue

            # Controls
            if ev.kind is Ev.FLUSH:
                full = self.win.full(as_float=True)
                text = (await self.engine.transcribe(full)).strip() if full.size else ""
                final_text = _stitch(self.hypothesis, text) if text else self.hypothesis
                if final_text:
                    yield ("FINAL", final_text)
                # reset for next utterance
                self._reset_state()

            elif ev.kind is Ev.END:
                full = self.win.full(as_float=True)
                text = (await self.engine.transcribe(full)).strip() if full.size else ""
                final_text = _stitch(self.hypothesis, text) if text else self.hypothesis
                if final_text:
                    yield ("FINAL", final_text)
                # end of session
                self._reset_state()
                break

    # ----------------- utils -------------------
    def _reset_state(self) -> None:
        self.win.clear()
        self._since_emit = 0
        self.hypothesis = ""


# ----------------- Tiny fake engine for demos/tests --------------------------
class _DurationEngine:
    """A tiny deterministic engine that returns the duration in ms as text.

    Useful for unit tests and wiring: it avoids pulling in any ASR model.
    """

    def __init__(self, sample_rate_hz: int = 16000):
        self.sr = sample_rate_hz

    async def transcribe(self, audio_f32: np.ndarray) -> str:  # type: ignore[override]
        await asyncio.sleep(0)
        ms = int(1000 * audio_f32.size / self.sr)
        return f"{ms}ms"


# ----------------- Self-demo -------------------------------------------------
async def _demo():
    eng = _DurationEngine()
    tr = Transcriber(eng, emit_partials=True, stride_ms=40, tail_ms=100)

    async def driver():
        # 3 audio frames: 20ms, 20ms, 10ms, then FLUSH, then END
        sr = 16000
        z20 = np.zeros((sr * 20) // 1000, dtype=np.int16).tobytes()
        z10 = np.zeros((sr * 10) // 1000, dtype=np.int16).tobytes()
        await tr.feed_audio(z20)
        await tr.feed_audio(z20)
        await tr.feed_audio(z10)
        await tr.flush()
        await tr.end()

    prod = asyncio.create_task(driver())
    async for kind, text in tr.run():
        print(kind, text)
    await prod

if __name__ == "__main__":
    asyncio.run(_demo())
