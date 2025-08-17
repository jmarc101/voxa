"""Sliding window for audio. PCM16 mono."""
from collections import deque
from typing import Optional
import numpy as np


class AudioSlidingWindow:
    """
    A tiny sliding (rolling) window for **PCM16 mono** audio.

    Why this exists
    ---------------
    - You stream PCM16 bytes in small frames (e.g., 20–40 ms each).
    - This class keeps only the **most recent `window_size_ms`** worth of samples.
    - You can grab either the **full window** or just the **tail** (latest X ms)
      as a NumPy array for decoding (partials) or finalization.

    Design choices
    --------------
    - Internally stores **int16 samples** (not bytes) for easy slicing.
    - Keeps memory bounded via a `deque(maxlen=...)`. When the buffer is full,
      pushing new samples automatically drops the oldest ones.
    - Mono-only

    Typical use
    -----------
    >>> win = AudioSlidingWindow(window_size_ms=3000, sample_rate_hz=16000)
    >>> n = win.append(pcm16_frame_bytes)   # returns number of samples appended
    >>> tail = win.tail_ms(2000)            # last 2s as int16 numpy array
    >>> full = win.full()                   # everything currently in the window

    Conversion to float
    -------------------
    - Most ASR models prefer float32 in [-1, 1]. Instead of storing float32
      (which uses 2x memory), we add an `as_float=True` flag on reads to convert
      only when needed.
    """

    # Public config knobs
    window_size_ms: int
    sample_rate_hz: int
    channels: int
    default_tail_ms: int

    # Derived / internal state
    max_samples: int                 # how many **samples** fit in the window
    buffer: deque[int]               # stores individual int16 samples
    _total_samples: int              # ever-seen sample counter (monotonic)

    def __init__(
        self,
        window_size_ms: int,
        sample_rate_hz: int = 16000,
        channels: int = 1,
        default_tail_ms: int = 2000,
    ) -> None:
        assert window_size_ms > 0, "window_size_ms must be > 0"
        assert sample_rate_hz > 0, "sample_rate_hz must be > 0"
        assert channels == 1, "Only mono is supported (channels=1)"

        self.window_size_ms = int(window_size_ms)
        self.sample_rate_hz = int(sample_rate_hz)
        self.channels = int(channels)
        self.default_tail_ms = int(default_tail_ms)

        # Max number of **mono** samples we keep at any time.
        # Example: 16_000 Hz * 3000 ms / 1000 = 48_000 samples (~96 KB @ int16)
        self.max_samples = (self.sample_rate_hz * self.window_size_ms) // 1000

        # Bounded buffer of **individual int16 samples**. As you append past
        # capacity, the deque automatically discards the oldest samples.
        self.buffer = deque(maxlen=self.max_samples)

        # Metrics / cadence counters
        self._total_samples = 0
        self._since_last_partial = 0

    # ---------------------------------------------------------------------
    # Append & Read APIs
    # ---------------------------------------------------------------------
    def append(self, pcm16_le: bytes) -> int:
        """Append a PCM16 **little-endian** mono frame.

        Parameters
        ----------
        pcm16_le : bytes
            Raw PCM16 little-endian audio (2 bytes per sample, mono).

        Returns
        -------
        int
            Number of **samples** appended (not bytes).

        Notes
        -----
        - We convert the bytes to a NumPy int16 array, then extend the deque
          with Python ints. This makes eviction by `maxlen` automatic.
        - If you ever need maximum throughput, consider a NumPy ring buffer
          instead of a deque to avoid Python-level per-element overhead.
        """
        # `np.int16` is little-endian on little-endian CPUs; if you want to be
        # explicit about endianness, use `np.dtype('<i2')` instead.
        arr = np.frombuffer(pcm16_le, dtype=np.int16)
        self.buffer.extend(arr.tolist())  # push individual samples
        n = int(arr.size)
        self._total_samples += n
        self._since_last_partial += n
        return n

    def _as_float(self, x: np.ndarray, as_float: bool) -> np.ndarray:
        """Convert int16 -> float32 in [-1, 1] if requested.

        This keeps the window memory-efficient (int16) while allowing callers
        to get float32 only when the model needs it.
        """
        if not as_float:
            return x
        # 32768.0 is the int16 full scale. Cast then scale to [-1, 1].
        return x.astype(np.float32) / 32768.0

    def tail_ms(self, ms: Optional[int] = None, *, as_float: bool = False) -> np.ndarray:
        """Return the most recent `ms` of samples as a NumPy array.

        If `ms` is None, use `default_tail_ms`.
        If `as_float` is True, return float32 in [-1, 1].
        """
        if ms is None:
            ms = self.default_tail_ms
        n_samples = max(0, (self.sample_rate_hz * int(ms)) // 1000)

        # Convert deque -> 1-D int16 array. This is a copy, which is fine for
        # small PoC windows. For very large windows, prefer a ring buffer.
        data = np.fromiter(self.buffer, dtype=np.int16, count=len(self.buffer))
        if n_samples == 0 or n_samples >= data.size:
            return self._as_float(data, as_float)
        tail = data[-n_samples:]
        return self._as_float(tail, as_float)

    def full(self, *, as_float: bool = False) -> np.ndarray:
        """Return **all** samples currently in the window as a NumPy array.

        If `as_float` is True, return float32 in [-1, 1].
        """
        data = np.fromiter(self.buffer, dtype=np.int16, count=len(self.buffer))
        return self._as_float(data, as_float)

    def clear(self) -> None:
        """Drop everything in the window.

        Typical use: after you emit a FINAL on FLUSH/END for an utterance.
        """
        self.buffer.clear()
        # NOTE: we intentionally **do not** reset _total_samples here so you
        # can still report "ever-seen" metrics. If you want per-utterance
        # counters, snapshot and compute deltas outside, or add a reset.
        self._since_last_partial = 0

    # ---------------------------------------------------------------------
    # Convenience metrics / cadence helpers
    # ---------------------------------------------------------------------
    @property
    def total_samples(self) -> int:
        """How many samples were ever appended to this window (monotonic)."""
        return self._total_samples

    @property
    def current_samples(self) -> int:
        """How many samples are currently stored (<= max_samples)."""
        return len(self.buffer)

    @property
    def current_duration_ms(self) -> int:
        """Approx duration (ms) currently held in the window."""
        return (1000 * len(self.buffer)) // self.sample_rate_hz

