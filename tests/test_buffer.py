"""Unit tests for ring buffer."""

import numpy as np
import pytest

from looplab.buffer.ring_buffer import RingBuffer


def test_ring_buffer_append_and_get_window():
    buf = RingBuffer(max_samples=10, n_channels=2)
    samples = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    ts = [1.0, 2.0, 3.0]
    buf.append(samples, ts)
    data, times = buf.get_window()
    assert data.shape == (3, 2)
    assert times.shape == (3,)
    np.testing.assert_array_almost_equal(data, samples)
    np.testing.assert_array_almost_equal(times, ts)
    assert buf.size == 3


def test_ring_buffer_wraps_around():
    buf = RingBuffer(max_samples=4, n_channels=1)
    for i in range(6):
        buf.append(np.array([[float(i)]]), [float(i)])
    data, times = buf.get_window()
    assert buf.size == 4
    # Should have last 4: 2, 3, 4, 5
    np.testing.assert_array_almost_equal(data.ravel(), [2.0, 3.0, 4.0, 5.0])
    np.testing.assert_array_almost_equal(times, [2.0, 3.0, 4.0, 5.0])


def test_ring_buffer_wrong_channels_raises():
    buf = RingBuffer(max_samples=10, n_channels=2)
    with pytest.raises(ValueError, match="channels"):
        buf.append(np.array([[1.0, 2.0, 3.0]]), [1.0])


def test_ring_buffer_empty_returns_empty_arrays():
    buf = RingBuffer(max_samples=10, n_channels=2)
    data, times = buf.get_window()
    assert data.shape == (0, 2)
    assert times.shape == (0,)
