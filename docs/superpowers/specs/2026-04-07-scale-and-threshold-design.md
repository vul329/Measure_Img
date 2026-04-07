# 倍率欄位與 Threshold 功能設計

日期：2026-04-07
專案：OptiMeasure_AOI

## 目標

為 OptiMeasure_AOI 新增兩項獨立功能：

1. **倍率與實際長度** — 在工具列新增倍率輸入欄，將圓形半徑與直線長度（pix）轉換為實際長度，顯示在量測表格中。
2. **Threshold 對話框** — 新增閥值化檢視功能，支援 histogram 顯示、Low/High 雙 slider 調整，以及在畫布上以使用者選定顏色高亮閥值範圍內的像素。

兩個功能彼此獨立，可分別實作與測試。

---

## 功能 (1)：倍率與實際長度

### 使用者互動

- 工具列「線寬」之後新增「倍率: [____]」欄位（純數字輸入框，不顯示單位）
- 使用者輸入倍率後：
  - 表格中所有圓形列的「實際長度」欄顯示 `radius * scale`（三位小數）
  - 表格中所有直線列的「實際長度」欄顯示 `length * scale`（三位小數）
  - 矩形類型固定顯示 `--`（本功能不支援矩形）
- 倍率為空字串或 0 時，所有實際長度欄顯示 `--`
- 倍率值持久化（QSettings），下次啟動恢復
- 載入新圖片時，倍率值保留（為使用者校正值）

### 元件變更

#### `views/toolbar.py`

- 新增成員：`_scale_edit: QLineEdit`，採 `QDoubleValidator(0, 99999, 6)`
- 在 `_build_style_controls()` 的線寬 SpinBox 之後加入：
  ```
  QLabel("倍率:") + self._scale_edit
  ```
- 新增信號：`scale_changed = Signal(float)`
- `textChanged` → 解析為 float（空字串或無法解析 → 0.0）→ emit `scale_changed`
- 從 `QSettings("OptiMeasure", "AOI")` 鍵 `toolbar/scale` 還原初值；變更時寫回

#### `models/shape_model.py`

- 新增成員：`_scale: float = 0.0`
- 新增方法：`set_scale(value: float)` — 更新後 emit 新信號 `scale_changed`
- 新增 property：`scale → float`

#### `views/right_panel.py`

- 表格欄數從 7 改為 8，新增第 8 欄標題「實際長度」
- `_table.setColumnCount(8)`，header label 加入 `"實際長度"`
- 第 8 欄寬度設為 100，`Interactive` 模式
- 新增成員：`_scale: float = 0.0`
- 新增方法：
  - `set_scale(value: float)` — 儲存 scale 並呼叫 `refresh_real_length_column()`
  - `refresh_real_length_column()` — 遍歷所有列，根據其類型與當前 `_scale` 重新填入第 7 欄（不重建其他欄）
  - `_compute_real_length(params: dict) → str` — 工具方法，回傳格式化字串或 `--`
- `_fill_row()` 末尾呼叫 `_set_cell(row, 7, self._compute_real_length(params))`

`_compute_real_length` 邏輯：

```
if self._scale <= 0:
    return "--"
if shape_type == 'Circle':
    return f"{params['radius'] * self._scale:.3f}"
if shape_type == 'Line':
    return f"{params['length'] * self._scale:.3f}"
return "--"
```

#### `controllers/main_controller.py`

接線新增：

- `toolbar.scale_changed → shape_model.set_scale`
- `toolbar.scale_changed → right_panel.set_scale`（簡化路徑：右側面板直接收 scale，避免經由 model 中轉）
- 註：`shape_model._scale` 與 `right_panel._scale` 各自持有，但都來自同一個信號源 `toolbar.scale_changed`，確保一致

### 邊界情況

- 倍率輸入「-3」：QDoubleValidator 下限 0，無法輸入
- 倍率輸入「abc」：解析失敗 → 視為 0.0 → 顯示 `--`
- 倍率為 0：顯示 `--`
- 表格已有圖形時改變倍率：`refresh_real_length_column()` 即時更新所有列
- 新圖載入：scale 保留

---

## 功能 (2)：Threshold 對話框

### 使用者互動

- 工具列新增按鈕「閥值」
- 點擊後彈出非模態對話框（可同時操作主視窗）
- 對話框內容：
  - 上方 Histogram（QPainter 自繪，256 bars + 兩條紅色垂直線標示 Low/High）
  - 中段：兩條 QSlider（0~255）+ 對應 QSpinBox（雙向同步），分別代表 Low 與 High
  - 下方：勾選方塊「顯示閥值」
  - 關閉按鈕
- 勾選「顯示閥值」後：
  - 畫布顯示閥值化結果：
    - **範圍內** `low <= gray <= high` → 顯示工具列當前線色
    - **範圍外** → 保持原本灰階值
  - 工具列線色變更時，閥值顯示顏色即時更新
- 對話框關閉但勾選仍為 True 時，畫布持續顯示閥值化結果
- 載入新圖時，閥值狀態自動重設（Low=0、High=255、取消勾選），對話框若已開啟則重新載入 histogram
- StatusBar 仍讀 `original_image`，不受閥值化影響

### 元件變更

#### 新檔案：`dialogs/threshold_dialog.py`

```
class HistogramWidget(QWidget):
    """純 QPainter 自繪 256-bin histogram，並標示 Low/High 垂直線"""

    def set_image(self, img: np.ndarray):
        # 若為彩色（3 通道）→ cv2.cvtColor(BGR2GRAY)
        # np.histogram(gray, 256, (0, 256)) → cache
        # update()

    def set_range(self, low: int, high: int):
        # 儲存後 update()

    def paintEvent(self, event):
        # 1. 背景填白
        # 2. 計算 bar 寬度 = width / 256
        # 3. 高度按 max(hist) 正規化繪製
        # 4. 在 low/high 對應 x 座標畫紅色垂直線


class ThresholdDialog(QDialog):
    """非模態，狀態持續"""

    threshold_changed = Signal(int, int, bool)  # low, high, enabled

    def __init__(self, parent=None):
        # setWindowFlags 加上 Qt.Tool（工具視窗）
        # setAttribute(Qt.WA_DeleteOnClose, False) — 避免關閉後被銷毀
        # 建立 HistogramWidget、兩組 slider+spinbox、checkbox

    def set_image(self, img: np.ndarray):
        # 傳給 _histogram.set_image()

    def reset(self):
        # low=0, high=255, checkbox=False
        # 不觸發信號（blockSignals）後手動 emit 一次最終狀態

    # slider/spinbox 任一變動 → 雙向同步 → emit threshold_changed
    # checkbox 變動 → emit threshold_changed
```

UI 大小參考：histogram 約 512×200，整個對話框約 540×360。

#### `models/image_model.py`

- 新增成員：
  - `_threshold_enabled: bool = False`
  - `_threshold_low: int = 0`
  - `_threshold_high: int = 255`
  - `_overlay_color: tuple[int, int, int] = (0, 255, 0)`（BGR）
- 新增方法：
  - `set_threshold(low: int, high: int, enabled: bool)` — 變更後 emit `visible_image_changed`
  - `set_overlay_color(color: QColor)` — 儲存為 BGR tuple；若 `_threshold_enabled` 為 True 則 emit `visible_image_changed`
- 既有信號 `display_image_updated` 重用即可（語意已是「顯示影像有變動」）。新增閥值或顏色變動時也 emit 此信號，避免引入新信號名稱。
- 新增方法 `get_visible_image() → np.ndarray`：
  - `enabled = False` → 回傳 `display_image`
  - `enabled = True`：
    1. 將 `display_image` 確保為灰階（彩色 → BGR2GRAY；彩色暫不支援，但仍應正常運作於灰階）
    2. `mask = (gray >= low) & (gray <= high)`
    3. 將灰階複製為 3 通道 BGR
    4. 在 mask 為 True 處填入 `_overlay_color`
    5. 回傳 BGR 影像
- 既有 `update_display_image()`（影像增強寫入處）也應 emit `visible_image_changed`，確保增強影響閥值結果

#### `views/image_view.py`

- 既有方法 `set_image(image_np)` 介面不變，但 controller 呼叫時改傳 `image_model.get_visible_image()` 而非 `display_image`
- 監聽 `image_model.display_image_updated` 的 controller 端 slot 改為呼叫 `image_view.set_image(image_model.get_visible_image())`

#### `views/toolbar.py`

- 新增 `QAction("閥值", self)`，新增信號 `threshold_clicked = Signal()`
- 既有 `color_changed` 信號保持不變

#### `controllers/main_controller.py`

接線新增：

- `toolbar.threshold_clicked → _on_threshold_clicked`：
  ```
  if self._threshold_dialog is None:
      self._threshold_dialog = ThresholdDialog(self.main_window)
      self._threshold_dialog.threshold_changed.connect(self._on_threshold_changed)
  if self.image_model.has_image:
      self._threshold_dialog.set_image(self.image_model.display_image)
  self._threshold_dialog.show()
  self._threshold_dialog.raise_()
  self._threshold_dialog.activateWindow()
  ```
- `_on_threshold_changed(low, high, enabled)` → `image_model.set_threshold(low, high, enabled)`
- 既有 `image_model.display_image_updated` 的 controller slot 統一呼叫 `image_view.set_image(image_model.get_visible_image())`
- `toolbar.color_changed → image_model.set_overlay_color`
- 載入新圖時：
  ```
  self.image_model.set_threshold(0, 255, False)
  if self._threshold_dialog is not None:
      self._threshold_dialog.reset()
      self._threshold_dialog.set_image(self.image_model.display_image)
  ```
- 影像增強對話框 apply 時：image_model 已 emit `visible_image_changed`，但 threshold_dialog 也應更新 histogram。新增：
  ```
  enhancement_dialog.applied → if threshold_dialog: threshold_dialog.set_image(display_image)
  ```

### 邊界情況

- Low > High：不限制（使用者責任），mask 為空，畫布全部顯示原灰階
- 沒載入圖片時點「閥值」按鈕：對話框可開啟，但 histogram 為空白；勾選顯示閥值無作用
- StatusBar pixel query 不受影響（仍讀 `original_image`）
- 線色由 QColor 儲存到 model 時轉為 BGR `(c.blue(), c.green(), c.red())`，因 OpenCV 影像為 BGR
- 非模態對話框生命週期由 controller 持有 reference，避免被 GC

---

## 兩個功能的相互作用

- 完全獨立：倍率只影響表格顯示；閥值只影響畫布顯示
- 載入新圖時：scale 保留、threshold 重設
- 工具列線色變更時：同時影響新繪圖形顏色 + 閥值高亮顏色

---

## 測試重點（手動）

### 倍率
- 空字串、0、負數（被擋）、正數的 4 種顯示
- 已有圖形時改倍率，所有列同步更新
- 重啟後倍率值保留
- 矩形列恆顯示 `--`

### 閥值
- Low/High 拖拉時 histogram 紅線同步移動
- 勾選後畫布即時切換顯示
- 取消勾選回到正常顯示
- 對話框關閉後勾選狀態若仍 True，畫布維持閥值顯示
- 工具列改線色 → 閥值高亮顏色即時變更
- 載入新圖 → 閥值重設、histogram 重算
- 影像增強 apply → histogram 重算、閥值結果同步更新
