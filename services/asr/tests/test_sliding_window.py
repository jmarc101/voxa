"""Audio sliding window implementation for processing PCM16 audio in chunks."""
import math
import numpy as np
import pytest

from core.sliding_window import AudioSlidingWindow

SR = 16000  # default sample rate used in tests


def pcm16_silence_ms(ms: int, sr: int = SR) -> bytes:
    """Return PCM16 LE silence for ms milliseconds."""
    n = (sr * ms) // 1000
    return np.zeros(n, dtype=np.int16).tobytes()


def pcm16_values(values: list[int]) -> bytes:
    """Helper to pack explicit int16 sample values into little-endian bytes."""
    return np.asarray(values, dtype=np.int16).tobytes()


def test_init_and_capacity():
    win = AudioSlidingWindow(window_size_ms=1000, sample_rate_hz=SR)
    assert win.max_samples == SR  # 1s window at 16 kHz
    assert win.current_samples == 0
    assert win.total_samples == 0


def test_append_counts_and_full():
    win = AudioSlidingWindow(window_size_ms=1000, sample_rate_hz=SR)
    # Append 3×20 ms frames => 60 ms total => 960 samples
    for _ in range(3):
        n = win.append(pcm16_silence_ms(20))
        assert n == (SR * 20) // 1000
    full = win.full()
    assert isinstance(full, np.ndarray)
    assert full.dtype == np.int16
    assert full.size == (SR * 60) // 1000
    assert win.current_samples == full.size
    assert win.total_samples == full.size  # ever-seen equals current so far


def test_tail_ms_behavior():
    win = AudioSlidingWindow(window_size_ms=1000, sample_rate_hz=SR)
    win.append(pcm16_silence_ms(100))  # 1600 samples
    tail = win.tail_ms(40)  # 640 samples
    assert tail.size == (SR * 40) // 1000
    # asking for more than present returns everything
    tail_big = win.tail_ms(500)
    assert tail_big.size == (SR * 100) // 1000


def test_rolling_eviction_at_capacity():
    win = AudioSlidingWindow(window_size_ms=100, sample_rate_hz=SR)  # 1600 samples cap
    win.append(pcm16_silence_ms(80))  # 1280
    win.append(pcm16_silence_ms(80))  # now 2560 appended; window should cap to 1600
    assert win.current_samples == (SR * 100) // 1000
    assert win.full().size == (SR * 100) // 1000
    # total_samples keeps growing (ever-seen)
    assert win.total_samples == (SR * 160) // 1000


def test_as_float_scaling():
    # Append known sample extremes to verify scaling
    win = AudioSlidingWindow(window_size_ms=1000, sample_rate_hz=SR)
    win.append(pcm16_values([-32768, 0, 32767]))
    f = win.full(as_float=True)
    assert f.dtype == np.float32
    assert math.isclose(float(f[0]), -1.0, rel_tol=0, abs_tol=1e-6)
    assert math.isclose(float(f[1]), 0.0, rel_tol=0, abs_tol=1e-6)
    # 32767 / 32768 ≈ 0.9999695
    assert math.isclose(float(f[2]), 32767.0 / 32768.0, rel_tol=0, abs_tol=1e-6)


def test_clear_resets_window_but_not_total():
    win = AudioSlidingWindow(window_size_ms=500, sample_rate_hz=SR)
    win.append(pcm16_silence_ms(50))
    seen = win.total_samples
    assert seen == (SR * 50) // 1000
    win.clear()
    assert win.current_samples == 0
    assert win.full().size == 0
    # total_samples is ever-seen and remains unchanged
    assert win.total_samples == seen


def test_current_duration_ms_matches_samples():
    win = AudioSlidingWindow(window_size_ms=1000, sample_rate_hz=SR)
    win.append(pcm16_silence_ms(125))  # 2000 samples at 16 kHz
    assert win.current_samples == 2000
    assert win.current_duration_ms == 125


def test_channels_assertion():
    with pytest.raises(AssertionError):
        AudioSlidingWindow(window_size_ms=1000, sample_rate_hz=SR, channels=2)
