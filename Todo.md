# 實作進度

## 分支
`feature/scale-threshold`
Worktree: `.worktrees/feature-scale-threshold`

## 計畫文件
- Spec: `docs/superpowers/specs/2026-04-07-scale-and-threshold-design.md`
- Plan: `docs/superpowers/plans/2026-04-07-scale-and-threshold.md`

---

## 任務清單

- [x] **Task 1: compute_real_length utility function** ✅ DONE (commit: b861b47)
  - `utils/measurement_utils.py` 新建，含 `compute_real_length()`
  - `right_panel.py` import 自 `utils.measurement_utils`
  - `tests/test_scale.py` 修正（negative scale 測試補上）
  - **→ 下一步：Task 2**

- [ ] **Task 2: Toolbar — scale field**
  - 修改 `OptiMeasure_AOI/views/toolbar.py`
  - 新增 `scale_changed = Signal(float)`, `QDoubleValidator`, scale QLineEdit, QSettings 持久化

- [ ] **Task 3: RightPanel — 8th column + scale wiring**
  - 修改 `OptiMeasure_AOI/views/right_panel.py`
  - 表格欄數 7→8，新增「實際長度」欄
  - 新增 `set_scale()`, `refresh_real_length_column()`, `_scale` 成員
  - `_fill_row()` 末尾呼叫 `compute_real_length()`

- [ ] **Task 4: Controller — wire scale**
  - 修改 `OptiMeasure_AOI/controllers/main_controller.py`
  - `toolbar.scale_changed → right_panel.set_scale`
  - `_connect_signals` 末尾加 `right_panel.set_scale(toolbar.scale)`

- [ ] **Task 5: apply_threshold_overlay utility + test**
  - 修改 `OptiMeasure_AOI/utils/image_utils.py`，新增 `apply_threshold_overlay(gray, low, high, overlay_bgr)`
  - 新增 `tests/test_threshold_overlay.py`

- [ ] **Task 6: ImageModel — threshold state**
  - 修改 `OptiMeasure_AOI/models/image_model.py`
  - 新增 `_threshold_enabled`, `_threshold_low`, `_threshold_high`, `_overlay_bgr`
  - 新增 `set_threshold()`, `set_overlay_color()`, `get_visible_image()`
  - import `apply_threshold_overlay`

- [ ] **Task 7: Controller — use get_visible_image()**
  - `_on_image_loaded` 和 `_on_display_image_updated` 改呼叫 `get_visible_image()`
  - `_on_color_changed` 同步呼叫 `image_model.set_overlay_color(color)`
  - `_connect_signals` 末尾加 `image_model.set_overlay_color(toolbar.current_color)`

- [ ] **Task 8: ThresholdDialog**
  - 新建 `OptiMeasure_AOI/dialogs/threshold_dialog.py`
  - `HistogramWidget(QWidget)` + `ThresholdDialog(QDialog)`
  - 非模態、`WA_DeleteOnClose=False`
  - `threshold_changed = Signal(int, int, bool)`

- [ ] **Task 9: Toolbar threshold button + Controller wiring**
  - Toolbar 新增 `threshold_clicked = Signal()` + 「閥值」QAction
  - Controller 新增 `_threshold_dialog`, `_on_threshold_clicked`, `_on_threshold_changed`
  - 載入新圖時 reset threshold
  - 增強 apply 時更新 histogram

---

## 注意事項

- compute_real_length 最終應從 `utils/measurement_utils.py` import，而非 `views/right_panel.py`
- Task 2 之前先修 Task 1 的 code review 問題
