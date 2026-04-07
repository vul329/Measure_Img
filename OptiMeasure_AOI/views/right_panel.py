"""
right_panel.py
右側面板（View 層）

上方：幾何參數輸入區（gen_circle, gen_rectangle1, gen_rectangle2, gen_line）
下方：QTableWidget 數據表格（顯示所有圖形參數，支援雙向連動）
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                                QLabel, QLineEdit, QPushButton, QTableWidget,
                                QTableWidgetItem, QHeaderView, QAbstractItemView,
                                QSizePolicy, QTabWidget)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDoubleValidator

from utils.measurement_utils import compute_real_length


class RightPanel(QWidget):
    # ── 信號 ──
    # 參數輸入產生圖形
    gen_circle_requested = Signal(float, float, float)        # cx, cy, radius
    gen_rect1_requested = Signal(float, float, float, float)  # col1, row1, col2, row2
    gen_rect2_requested = Signal(float, float, float, float, float)  # cx, cy, angle, hw, hh
    gen_line_requested = Signal(float, float, float, float)   # x1, y1, x2, y2
    # 表格選取變更 → 通知 Controller 高亮對應圖形
    table_row_selected = Signal(int)   # shape_id
    # 表格行刪除 → 通知 Controller 移除圖形
    table_row_deleted = Signal(int)    # shape_id
    # 刪除所有圖形
    table_all_deleted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(280)
        self.setMaximumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # 上方：參數輸入
        layout.addWidget(self._build_param_group())
        # 下方：數據表格（佔用剩餘空間）
        layout.addWidget(self._build_table_group(), stretch=1)

        # 內部映射：row index → shape_id
        self._row_to_id: dict[int, int] = {}

    # ──────────────────────────────────────────────
    # 參數輸入區
    # ──────────────────────────────────────────────

    def _build_param_group(self) -> QGroupBox:
        group = QGroupBox("幾何參數輸入")
        tab = QTabWidget()

        tab.addTab(self._build_circle_tab(), "圓形")
        tab.addTab(self._build_rect1_tab(), "正交矩形")
        tab.addTab(self._build_rect2_tab(), "旋轉矩形")
        tab.addTab(self._build_line_tab(), "直線")

        vbox = QVBoxLayout(group)
        vbox.addWidget(tab)
        return group

    def _make_float_edit(self, placeholder: str = "0.0") -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setValidator(QDoubleValidator(-99999, 99999, 4))
        return edit

    def _build_circle_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(4)

        self._circle_cx = self._make_float_edit("cx（欄）")
        self._circle_cy = self._make_float_edit("cy（列）")
        self._circle_r = self._make_float_edit("radius（半徑）")
        btn = QPushButton("gen_circle")
        btn.clicked.connect(self._on_gen_circle)

        for lbl, edit in [("cx:", self._circle_cx), ("cy:", self._circle_cy),
                          ("r:", self._circle_r)]:
            row = QHBoxLayout()
            row.addWidget(QLabel(lbl))
            row.addWidget(edit)
            layout.addLayout(row)
        layout.addWidget(btn)
        layout.addStretch()
        return w

    def _build_rect1_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(4)

        self._r1_col1 = self._make_float_edit("col1（左）")
        self._r1_row1 = self._make_float_edit("row1（上）")
        self._r1_col2 = self._make_float_edit("col2（右）")
        self._r1_row2 = self._make_float_edit("row2（下）")
        btn = QPushButton("gen_rectangle1")
        btn.clicked.connect(self._on_gen_rect1)

        for lbl, edit in [("col1:", self._r1_col1), ("row1:", self._r1_row1),
                          ("col2:", self._r1_col2), ("row2:", self._r1_row2)]:
            row = QHBoxLayout()
            row.addWidget(QLabel(lbl))
            row.addWidget(edit)
            layout.addLayout(row)
        layout.addWidget(btn)
        layout.addStretch()
        return w

    def _build_rect2_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(4)

        self._r2_cx = self._make_float_edit("cx")
        self._r2_cy = self._make_float_edit("cy")
        self._r2_angle = self._make_float_edit("angle（度）")
        self._r2_hw = self._make_float_edit("half_width")
        self._r2_hh = self._make_float_edit("half_height")
        btn = QPushButton("gen_rectangle2")
        btn.clicked.connect(self._on_gen_rect2)

        for lbl, edit in [("cx:", self._r2_cx), ("cy:", self._r2_cy),
                          ("angle:", self._r2_angle), ("hw:", self._r2_hw),
                          ("hh:", self._r2_hh)]:
            row = QHBoxLayout()
            row.addWidget(QLabel(lbl))
            row.addWidget(edit)
            layout.addLayout(row)
        layout.addWidget(btn)
        layout.addStretch()
        return w

    def _build_line_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(4)

        self._line_x1 = self._make_float_edit("x1")
        self._line_y1 = self._make_float_edit("y1")
        self._line_x2 = self._make_float_edit("x2")
        self._line_y2 = self._make_float_edit("y2")
        btn = QPushButton("gen_line")
        btn.clicked.connect(self._on_gen_line)

        for lbl, edit in [("x1:", self._line_x1), ("y1:", self._line_y1),
                          ("x2:", self._line_x2), ("y2:", self._line_y2)]:
            row = QHBoxLayout()
            row.addWidget(QLabel(lbl))
            row.addWidget(edit)
            layout.addLayout(row)
        layout.addWidget(btn)
        layout.addStretch()
        return w

    # ──────────────────────────────────────────────
    # 參數輸入信號
    # ──────────────────────────────────────────────

    def _parse(self, edit: QLineEdit, default: float = 0.0) -> float:
        try:
            return float(edit.text())
        except ValueError:
            return default

    def _on_gen_circle(self):
        self.gen_circle_requested.emit(
            self._parse(self._circle_cx),
            self._parse(self._circle_cy),
            max(1.0, self._parse(self._circle_r, 50.0)))

    def _on_gen_rect1(self):
        self.gen_rect1_requested.emit(
            self._parse(self._r1_col1),
            self._parse(self._r1_row1),
            self._parse(self._r1_col2, 100.0),
            self._parse(self._r1_row2, 100.0))

    def _on_gen_rect2(self):
        self.gen_rect2_requested.emit(
            self._parse(self._r2_cx),
            self._parse(self._r2_cy),
            self._parse(self._r2_angle),
            max(1.0, self._parse(self._r2_hw, 50.0)),
            max(1.0, self._parse(self._r2_hh, 30.0)))

    def _on_gen_line(self):
        self.gen_line_requested.emit(
            self._parse(self._line_x1),
            self._parse(self._line_y1),
            self._parse(self._line_x2, 100.0),
            self._parse(self._line_y2, 100.0))

    # ──────────────────────────────────────────────
    # 數據表格
    # ──────────────────────────────────────────────

    def _build_table_group(self) -> QGroupBox:
        group = QGroupBox("量測數據")
        layout = QVBoxLayout(group)

        # 建立表格
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["ID", "類型", "參數1", "參數2", "參數3", "參數4", "參數5"])
        # 各欄依內容自動調整寬度，超出時出現水平捲軸
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 類型
        for col in range(2, 7):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            self._table.setColumnWidth(col, 90)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)  # 唯讀
        self._table.verticalHeader().setVisible(False)

        # 按鈕列
        btn_layout = QHBoxLayout()
        del_btn = QPushButton("刪除選取圖形")
        del_btn.clicked.connect(self._on_delete_selected)
        del_all_btn = QPushButton("刪除所有圖形")
        del_all_btn.clicked.connect(self._on_delete_all)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(del_all_btn)

        layout.addWidget(self._table)
        layout.addLayout(btn_layout)

        # 連接表格選取信號
        self._table.itemSelectionChanged.connect(self._on_table_selection_changed)

        return group

    # ──────────────────────────────────────────────
    # 表格更新介面（由 Controller 呼叫）
    # ──────────────────────────────────────────────

    def add_shape_row(self, shape):
        """新增圖形時，在表格末尾插入一列"""
        params = shape.get_params()
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._row_to_id[row] = shape.shape_id
        self._fill_row(row, shape.shape_id, params)

    def update_shape_row(self, shape):
        """圖形參數更新時，找到對應列並刷新數值"""
        params = shape.get_params()
        row = self._find_row_by_id(shape.shape_id)
        if row >= 0:
            self._fill_row(row, shape.shape_id, params)

    def remove_shape_row(self, shape):
        """移除圖形時，從表格刪除對應列"""
        row = self._find_row_by_id(shape.shape_id)
        if row >= 0:
            self._table.removeRow(row)
            # 重建 row → id 映射（列號因刪除而改變）
            self._rebuild_row_map()

    def highlight_shape_row(self, shape_id: int):
        """從畫布選取圖形時，高亮表格對應列"""
        row = self._find_row_by_id(shape_id)
        if row >= 0:
            self._table.blockSignals(True)
            self._table.selectRow(row)
            self._table.blockSignals(False)

    # ──────────────────────────────────────────────
    # 表格內部工具方法
    # ──────────────────────────────────────────────

    def _fill_row(self, row: int, shape_id: int, params: dict):
        """依 params 字典填入表格資料"""
        # 欄 0：ID
        self._set_cell(row, 0, str(shape_id))
        # 欄 1：類型
        self._set_cell(row, 1, params.get('type', ''))

        # 欄 2~6：依類型填入不同參數
        shape_type = params.get('type', '')
        if shape_type == 'Circle':
            self._set_cell(row, 2, f"cx={params.get('cx', '')}")
            self._set_cell(row, 3, f"cy={params.get('cy', '')}")
            self._set_cell(row, 4, f"r={params.get('radius', '')}")
            self._set_cell(row, 5, '')
            self._set_cell(row, 6, '')
        elif shape_type == 'Rect1':
            self._set_cell(row, 2, f"col1={params.get('col1', '')}")
            self._set_cell(row, 3, f"row1={params.get('row1', '')}")
            self._set_cell(row, 4, f"col2={params.get('col2', '')}")
            self._set_cell(row, 5, f"row2={params.get('row2', '')}")
            self._set_cell(row, 6, f"w={params.get('width', '')} h={params.get('height', '')}")
        elif shape_type == 'Rect2':
            self._set_cell(row, 2, f"cx={params.get('cx', '')}")
            self._set_cell(row, 3, f"cy={params.get('cy', '')}")
            self._set_cell(row, 4, f"ang={params.get('angle', '')}")
            self._set_cell(row, 5, f"hw={params.get('half_width', '')}")
            self._set_cell(row, 6, f"hh={params.get('half_height', '')}")
        elif shape_type == 'Line':
            self._set_cell(row, 2, f"x1={params.get('x1', '')}")
            self._set_cell(row, 3, f"y1={params.get('y1', '')}")
            self._set_cell(row, 4, f"x2={params.get('x2', '')}")
            self._set_cell(row, 5, f"y2={params.get('y2', '')}")
            self._set_cell(row, 6, f"len={params.get('length', '')}")

    def _set_cell(self, row: int, col: int, text: str):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, col, item)

    def _find_row_by_id(self, shape_id: int) -> int:
        """搜尋表格中 shape_id 對應的列索引，找不到回傳 -1"""
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item and item.text() == str(shape_id):
                return row
        return -1

    def _rebuild_row_map(self):
        """重建 row → shape_id 的映射（列刪除後索引會改變）"""
        self._row_to_id.clear()
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item:
                try:
                    self._row_to_id[row] = int(item.text())
                except ValueError:
                    pass

    def _on_table_selection_changed(self):
        """表格選取變更 → 通知 Controller 高亮畫布圖形"""
        rows = self._table.selectedItems()
        if not rows:
            return
        row = self._table.currentRow()
        id_item = self._table.item(row, 0)
        if id_item:
            try:
                self.table_row_selected.emit(int(id_item.text()))
            except ValueError:
                pass

    def _on_delete_selected(self):
        """刪除按鈕：通知 Controller 移除選取的圖形"""
        row = self._table.currentRow()
        if row < 0:
            return
        id_item = self._table.item(row, 0)
        if id_item:
            try:
                self.table_row_deleted.emit(int(id_item.text()))
            except ValueError:
                pass

    def _on_delete_all(self):
        """刪除所有圖形：通知 Controller 清除全部"""
        if self._table.rowCount() > 0:
            self.table_all_deleted.emit()
