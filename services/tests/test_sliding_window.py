import math
import numpy as np

from services.asr.core.sliding_window import AudioSlidingWindow

SR = 16000  # default sample rate used in tests
SR_MS = SR // 1000  # samples per millisecond


def pcm16_value_ms_repeat(value: int, ms: int) -> bytes:
    """Helper to repeat a value for ms milliseconds."""
    n = SR_MS * ms
    return np.full(n, value, dtype=np.int16).tobytes()


def test_init_defaults():
    win = AudioSlidingWindow(window_size_ms=3000)
    assert win.max_samples == SR_MS * 3000  # 1s window at 16 kHz
    assert win.current_samples == 0
    assert win.total_samples == 0
    assert win.default_tail_ms == 2000
    assert win.window_size_ms == 3000
    assert win.sample_rate_hz == SR


def test_init_custom():
    win = AudioSlidingWindow(window_size_ms=1000, sample_rate_hz=48000, default_tail_ms=1500)
    assert win.max_samples == 48000
    assert win.default_tail_ms == 1000  # default tail is capped at window size
    assert win.window_size_ms == 1000
    assert win.sample_rate_hz == 48000


def test_append_counts_and_full():
    win = AudioSlidingWindow(window_size_ms=500, sample_rate_hz=SR)
    win.append(pcm16_value_ms_repeat(0, 100))
    assert win.current_duration_ms == 100
    assert win.total_samples == SR_MS * 100
    full = win.full()
    assert full.size == SR_MS * 100
    assert full.dtype == np.int16
    assert full.mean() == 0  # 0 mean should be 0 since we appended silence for 100ms

    # append 50 for 500ms
    win.append(pcm16_value_ms_repeat(50, 500))
    assert win.current_duration_ms == 500
    assert win.current_samples == SR_MS * 500
    assert win.total_samples == SR_MS * 600  # 100 + 500
    assert win.current_duration_ms == 500
    full = win.full()
    assert full.size == SR_MS * 500
    assert full.dtype == np.int16
    assert full.mean() == 50  # 50 mean should be 50 since we appended 50 for 500ms


def test_tail_ms_behavior():
    win = AudioSlidingWindow(window_size_ms=1000, sample_rate_hz=SR)
    win.append(pcm16_value_ms_repeat(0, 100))
    tail = win.tail_ms(40)
    assert tail.size == SR_MS * 40
    assert tail.mean() == 0  # 0 mean should be 0 since we appended silence

    win.append(pcm16_value_ms_repeat(20, 50))
    tail = win.tail_ms(100)
    assert tail.size == SR_MS * 100
    assert tail.mean() == 10  # 10 mean since we appended 20 for half of 100ms (silence before)


def test_rolling_eviction_at_capacity():
    win = AudioSlidingWindow(window_size_ms=100, sample_rate_hz=SR)
    win.append(pcm16_value_ms_repeat(0, 160))  # 1280
    assert win.current_samples == SR_MS * 100
    assert win.full().size == SR_MS * 100
    # total_samples keeps growing (ever-seen)
    assert win.total_samples == SR_MS * 160

    win.clear()
    assert win.current_samples == 0
    assert win.full().size == 0
    assert win.total_samples == SR_MS * 160


def test_as_float_scaling():
    win = AudioSlidingWindow(window_size_ms=1000, sample_rate_hz=SR)
    win.append(pcm16_value_ms_repeat(-32768, 100))
    f = win.full(as_float=True)
    assert f.dtype == np.float32
    assert math.isclose(float(f[0]), -1.0, rel_tol=0, abs_tol=1e-6)
