# tests/test_caliper.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'OptiMeasure_AOI'))

import numpy as np
import cv2
import pytest
from utils.image_utils import caliper_find_circle


def _circle_image(cx=150, cy=150, r=80):
    """灰階影像，白色圓環，黑色背景（厚度 2px）"""
    img = np.zeros((300, 300), dtype=np.uint8)
    cv2.circle(img, (cx, cy), r, 255, 2)
    return img


def test_basic_detection():
    """精確圓應被正確擬合（誤差 < 2px）"""
    img = _circle_image()
    result = caliper_find_circle(img, 150.0, 150.0, 80.0)
    assert result['success'] is True
    assert abs(result['cx'] - 150) < 2
    assert abs(result['cy'] - 150) < 2
    assert abs(result['radius'] - 80) < 2


def test_approx_offset():
    """近似值偏移 5px 仍應收斂（誤差 < 5px）"""
    img = _circle_image()
    result = caliper_find_circle(img, 155.0, 148.0, 75.0)
    assert result['success'] is True
    assert abs(result['cx'] - 150) < 5
    assert abs(result['cy'] - 150) < 5
    assert abs(result['radius'] - 80) < 5


def test_dark_to_light():
    """edge_dir='dark_to_light' 應成功偵測"""
    img = _circle_image()
    result = caliper_find_circle(img, 150.0, 150.0, 80.0,
                                  edge_dir='dark_to_light')
    assert result['success'] is True


def test_color_image():
    """BGR 彩色影像應自動轉灰階後偵測"""
    gray = _circle_image()
    color = np.stack([gray, gray, gray], axis=2)
    result = caliper_find_circle(color, 150.0, 150.0, 80.0)
    assert result['success'] is True


def test_return_keys():
    """回傳 dict 必須包含所有必要 key"""
    img = _circle_image()
    result = caliper_find_circle(img, 150.0, 150.0, 80.0)
    for key in ('cx', 'cy', 'radius', 'inliers', 'total', 'success'):
        assert key in result


def test_inliers_count():
    """inliers 不超過 total"""
    img = _circle_image()
    result = caliper_find_circle(img, 150.0, 150.0, 80.0)
    assert result['inliers'] <= result['total']
