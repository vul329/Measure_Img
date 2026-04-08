"""
measurement_utils.py
量測計算工具函式
"""


def compute_real_length(params: dict, scale: float) -> str:
    """
    Convert pixel measurement to real-world length using scale factor.
    Returns '--' when scale is 0 or negative, or shape type is not Circle/Line.
    """
    if scale <= 0:
        return '--'
    shape_type = params.get('type', '')
    if shape_type == 'Circle':
        return f"{params.get('radius', 0.0) * scale:.5f}"
    if shape_type == 'Line':
        return f"{params.get('length', 0.0) * scale:.5f}"
    return '--'
