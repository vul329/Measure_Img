# Todo

## 待實作功能

### 卡尺抓圓（Caliper Circle Detection）

**設計方向：獨立按鈕（方向 B）**

工具列新增「卡尺抓圓」模式。在此模式下拖曳畫出近似圓，自動執行卡尺偵測並以擬合結果產生 CircleItem。

#### 演算法流程
1. 使用者在 `CALIPER_CIRCLE` 模式下拖曳畫出近似圓（中心 + 半徑）
2. 從中心向外射出 N 條輻射射線（預設 36 條，每 10°）
3. 沿每條射線在搜尋帶（近似半徑 ±20%）內取樣像素剖面
4. 對每條剖面計算 1D 梯度，找到梯度最大點作為邊緣位置
5. 收集 N 個邊緣點，用最小二乘法擬合圓（求 cx, cy, r）
6. RANSAC 剔除離群點後再擬合，提高準確度
7. 以擬合結果產生 CircleItem 加入畫布與表格

#### 可調參數（透過 CaliperCircleDialog）
| 參數 | 預設值 | 範圍 |
|------|--------|------|
| 射線數 | 36 | 12 ~ 72 |
| 搜尋帶寬 | ±20% | ±5% ~ ±50% |
| 梯度方向 | 不限 | 暗→亮 / 亮→暗 / 不限 |
| RANSAC 容忍誤差 | 2 px | 1 ~ 5 px |

#### 需新增 / 修改的檔案
```
新增：
  utils/image_utils.py          → caliper_find_circle(image, cx, cy, radius, ...) 函式
  dialogs/caliper_dialog.py     → 參數設定面板 + 偵測結果顯示

修改：
  views/image_view.py           → 新增 ViewMode.CALIPER_CIRCLE
  views/toolbar.py              → 新增「卡尺抓圓」按鈕
  controllers/main_controller.py → 連接卡尺偵測流程與 CircleItem 建立
```

#### 效能預估
- 36 條射線 × 100 取樣點，純 numpy 實作
- 10MP 影像執行時間 < 10ms
