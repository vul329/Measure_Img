import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'OptiMeasure_AOI'))

from utils.measurement_utils import compute_real_length


def test_scale_zero_returns_dashes():
    params = {'type': 'Circle', 'radius': 50.0}
    assert compute_real_length(params, 0.0) == '--'


def test_scale_negative_returns_dashes():
    params = {'type': 'Circle', 'radius': 50.0}
    assert compute_real_length(params, -1.0) == '--'


def test_circle_real_length():
    params = {'type': 'Circle', 'radius': 12.5}
    assert compute_real_length(params, 0.8) == '10.000'


def test_line_real_length():
    params = {'type': 'Line', 'length': 100.0}
    assert compute_real_length(params, 0.1) == '10.000'


def test_rect_always_dashes():
    params = {'type': 'Rect1', 'width': 50.0, 'height': 30.0}
    assert compute_real_length(params, 2.0) == '--'


def test_three_decimal_precision():
    params = {'type': 'Circle', 'radius': 10.0}
    assert compute_real_length(params, 1.2345) == '12.345'
