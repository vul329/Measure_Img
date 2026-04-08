import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'OptiMeasure_AOI'))

import numpy as np
from utils.image_utils import apply_threshold_overlay


def test_outside_range_keeps_gray():
    """Pixels outside [low, high] keep their grayscale value as BGR."""
    gray = np.array([[50]], dtype=np.uint8)
    result = apply_threshold_overlay(gray, 100, 200, (0, 255, 0))
    assert result.shape == (1, 1, 3)
    assert result[0, 0, 0] == 50  # B
    assert result[0, 0, 1] == 50  # G
    assert result[0, 0, 2] == 50  # R


def test_inside_range_gets_overlay_color():
    """Pixels in [low, high] are replaced with overlay_bgr."""
    gray = np.array([[150]], dtype=np.uint8)
    result = apply_threshold_overlay(gray, 100, 200, (0, 255, 0))
    assert result[0, 0, 0] == 0    # B
    assert result[0, 0, 1] == 255  # G
    assert result[0, 0, 2] == 0    # R


def test_boundary_pixels_are_inside():
    """Boundary values (exactly low or high) are inside the range."""
    gray = np.array([[100, 200]], dtype=np.uint8)
    result = apply_threshold_overlay(gray, 100, 200, (255, 0, 0))
    assert result[0, 0, 0] == 255  # low boundary → overlay
    assert result[0, 1, 0] == 255  # high boundary → overlay


def test_mixed_row():
    """Three pixels: below, inside, above range."""
    gray = np.array([[50, 150, 250]], dtype=np.uint8)
    result = apply_threshold_overlay(gray, 100, 200, (0, 0, 255))
    # pixel 0 (50) outside → gray
    assert result[0, 0, 2] == 50
    # pixel 1 (150) inside → R=255
    assert result[0, 1, 2] == 255
    # pixel 2 (250) outside → gray
    assert result[0, 2, 2] == 250


def test_output_is_bgr_uint8():
    gray = np.zeros((10, 10), dtype=np.uint8)
    result = apply_threshold_overlay(gray, 0, 255, (100, 150, 200))
    assert result.dtype == np.uint8
    assert result.ndim == 3
    assert result.shape[2] == 3
