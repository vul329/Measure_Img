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
