"""
image_utils.py
影像處理工具函式（OpenCV 底層運算）
"""
import numpy as np
import cv2


def apply_gamma(image: np.ndarray, gamma: float) -> np.ndarray:
    """
    Gamma 校正：用於拉提暗部細節或壓制亮部。
    gamma < 1 → 影像變亮；gamma > 1 → 影像變暗。

    使用查找表 (LUT) 實現高效向量化運算，避免逐像素迴圈。
    """
    if gamma <= 0:
        gamma = 0.01
    # 建立 256 長度的 LUT：output = 255 * (input/255)^(1/gamma)
    inv_gamma = 1.0 / gamma
    lut = np.array([
        min(255, int((i / 255.0) ** inv_gamma * 255))
        for i in range(256)
    ], dtype=np.uint8)
    return cv2.LUT(image, lut)


def apply_linear(image: np.ndarray, gain: float, offset: float) -> np.ndarray:
    """
    線性縮放（對比/亮度）：output = gain * input + offset
    gain > 1 → 增加對比；offset > 0 → 增加亮度。

    使用 numpy clip 避免溢位，向量化運算效能佳。
    """
    # 先轉 float32 再運算，避免 uint8 溢位問題
    result = image.astype(np.float32) * gain + offset
    # 截斷至 [0, 255] 並轉回 uint8
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_enhancements(image: np.ndarray, gamma: float, gain: float, offset: float) -> np.ndarray:
    """
    依序套用 Gamma 校正與線性縮放。
    此函式由影像增強 Dialog 呼叫，作用於 display_image。
    """
    result = apply_gamma(image, gamma)
    result = apply_linear(result, gain, offset)
    return result


def crop_roi(image: np.ndarray, center_x: int, center_y: int, half_size: int) -> np.ndarray:
    """
    從原始影像中擷取以 (center_x, center_y) 為中心，邊長 = half_size*2+1 的 ROI。
    使用 numpy slicing，不複製整張影像，效能高。

    超出邊界的部分以黑色填補（pad_mode='constant'）。

    回傳值：ROI numpy array（uint8）
    """
    h, w = image.shape[:2]
    x1 = center_x - half_size
    y1 = center_y - half_size
    x2 = center_x + half_size + 1
    y2 = center_y + half_size + 1

    # 計算需要 padding 的量
    pad_top = max(0, -y1)
    pad_bottom = max(0, y2 - h)
    pad_left = max(0, -x1)
    pad_right = max(0, x2 - w)

    # 實際讀取範圍（裁剪至影像邊界內）
    rx1 = max(0, x1)
    ry1 = max(0, y1)
    rx2 = min(w, x2)
    ry2 = min(h, y2)

    roi = image[ry1:ry2, rx1:rx2]

    # 若需要 padding（游標靠近邊緣時），以黑色填補
    if pad_top or pad_bottom or pad_left or pad_right:
        if image.ndim == 2:
            roi = np.pad(roi, ((pad_top, pad_bottom), (pad_left, pad_right)),
                         mode='constant', constant_values=0)
        else:
            roi = np.pad(roi, ((pad_top, pad_bottom), (pad_left, pad_right), (0, 0)),
                         mode='constant', constant_values=0)

    return roi


def caliper_find_circle(
    image: np.ndarray,
    cx: float,
    cy: float,
    radius: float,
    n_rays: int = 36,
    band_ratio: float = 0.20,
    edge_dir: str = 'any',
    ransac_tol: float = 2.0,
) -> dict:
    """
    射線卡尺偵測圓形邊緣，最小二乘法 + RANSAC 擬合圓。

    Parameters
    ----------
    image      : 灰階或 BGR 彩色 numpy array
    cx, cy     : 近似圓心（像素座標）
    radius     : 近似半徑
    n_rays     : 射線數（預設 36）
    band_ratio : 搜尋帶半寬比例（預設 ±20%）
    edge_dir   : 'any' | 'dark_to_light' | 'light_to_dark'
    ransac_tol : RANSAC inlier 距離容忍（像素）

    Returns
    -------
    dict with keys: cx, cy, radius, inliers, total, success
    """
    # 轉灰階
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    else:
        gray = image.astype(np.float32)

    h, w = gray.shape
    r_min = radius * (1.0 - band_ratio)
    r_min = max(0.0, r_min)
    r_max = radius * (1.0 + band_ratio)
    n_samples = max(20, int((r_max - r_min) * 2) + 10)

    _VALID_EDGE_DIRS = ('any', 'dark_to_light', 'light_to_dark')
    if edge_dir not in _VALID_EDGE_DIRS:
        raise ValueError(f"edge_dir must be one of {_VALID_EDGE_DIRS}, got {edge_dir!r}")

    angles = np.linspace(0.0, 2.0 * np.pi, n_rays, endpoint=False)
    edge_pts: list[tuple[float, float]] = []

    for angle in angles:
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        distances = np.linspace(r_min, r_max, n_samples)
        xs = np.clip(cx + distances * cos_a, 0, w - 1).astype(int)
        ys = np.clip(cy + distances * sin_a, 0, h - 1).astype(int)
        profile = gray[ys, xs]
        gradient = np.gradient(profile)

        if np.max(np.abs(gradient)) == 0.0:
            continue  # 無梯度（均勻區域），跳過此射線

        if edge_dir == 'dark_to_light':
            idx = int(np.argmax(gradient))
        elif edge_dir == 'light_to_dark':
            idx = int(np.argmin(gradient))
        else:
            idx = int(np.argmax(np.abs(gradient)))

        edge_pts.append((cx + distances[idx] * cos_a,
                         cy + distances[idx] * sin_a))

    _FAIL = {'cx': cx, 'cy': cy, 'radius': radius,
             'inliers': 0, 'total': n_rays, 'success': False}

    if len(edge_pts) < 3:
        return _FAIL

    pts = np.array(edge_pts, dtype=np.float64)

    def _fit_circle(p: np.ndarray):
        """代數最小二乘法：(x-cx)²+(y-cy)²=r²"""
        x, y = p[:, 0], p[:, 1]
        A = np.column_stack([x, y, np.ones(len(x))])
        b_vec = -(x ** 2 + y ** 2)
        coef, _, _, _ = np.linalg.lstsq(A, b_vec, rcond=None)
        a, b, c = coef
        fit_cx, fit_cy = -a / 2.0, -b / 2.0
        val = fit_cx ** 2 + fit_cy ** 2 - c
        if val <= 0:
            return None
        return fit_cx, fit_cy, float(np.sqrt(val))

    # RANSAC
    rng = np.random.default_rng(42)
    best_mask = np.zeros(len(pts), dtype=bool)

    for _ in range(50):
        idx3 = rng.choice(len(pts), 3, replace=False)
        res = _fit_circle(pts[idx3])
        if res is None:
            continue
        fcx, fcy, fr = res
        dist = np.abs(np.sqrt((pts[:, 0] - fcx) ** 2 +
                               (pts[:, 1] - fcy) ** 2) - fr)
        mask = dist <= ransac_tol
        if mask.sum() > best_mask.sum():
            best_mask = mask

    if best_mask.sum() < 3:
        return _FAIL

    final = _fit_circle(pts[best_mask])
    if final is None:
        return _FAIL

    fcx, fcy, fr = final
    return {
        'cx': float(fcx), 'cy': float(fcy), 'radius': float(fr),
        'inliers': int(best_mask.sum()), 'total': n_rays,
        'success': True,
    }


def numpy_to_qimage(image: np.ndarray):
    """
    將 numpy array（OpenCV 格式）轉換為 QImage，供 PySide6 顯示。
    支援灰階（2D array）與彩色（3D BGR array）。
    """
    from PySide6.QtGui import QImage

    if image is None:
        return None

    if image.ndim == 2:
        # 灰階影像：8 位元單通道
        h, w = image.shape
        bytes_per_line = w
        # 確保記憶體連續（OpenCV 某些操作後可能不連續）
        img_contiguous = np.ascontiguousarray(image)
        return QImage(img_contiguous.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
    else:
        # 彩色影像：OpenCV 使用 BGR，需轉為 RGB
        h, w, ch = image.shape
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        bytes_per_line = w * 3
        img_contiguous = np.ascontiguousarray(img_rgb)
        return QImage(img_contiguous.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
