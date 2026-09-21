"""
Interactive screen annotation and drawing canvas overlay.
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PyQt6.QtWidgets import (
    QWidget,
    QApplication,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QButtonGroup,
    QComboBox,
    QColorDialog,
)


class DrawItem:
    """Represents a discrete drawn object."""

    def __init__(
        self,
        tool: str,
        color: QColor,
        width: int,
        points: List[QPoint],
        text: str = "",
        number: int = 1,
    ):
        self.tool = tool
        self.color = color
        self.width = width
        self.points = points
        self.text = text
        self.number = number


class AnnotationCanvas(QWidget):
    """Full-screen transparent drawing canvas for live screen markup."""

    closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setGeometry(QApplication.primaryScreen().virtualGeometry())

        self.current_tool = "pen"  # pen, highlighter, arrow, rect, circle, badge, text, blur
        self.current_color = QColor("#EF4444")
        self.stroke_width = 4
        self.badge_counter = 1

        self.items: List[DrawItem] = []
        self.redo_stack: List[DrawItem] = []
        self.current_points: List[QPoint] = []
        self.is_drawing = False

        self._setup_toolbar()

    def _setup_toolbar(self):
        """Floating tool selector palette."""
        self.toolbar = QFrame(self)
        self.toolbar.setStyleSheet("""
            QFrame {
                background-color: rgba(22, 24, 32, 0.95);
                border: 1px solid #3F4458;
                border-radius: 12px;
                padding: 6px;
            }
            QPushButton {
                background-color: #20232E;
                color: #F9FAFB;
                border: 1px solid #2D313F;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                min-width: 24px;
            }
            QPushButton:hover {
                background-color: #2B2F3D;
                border-color: #6366F1;
            }
            QPushButton:checked {
                background-color: #6366F1;
                border-color: #4F46E5;
                color: white;
                font-weight: bold;
            }
        """)

        layout = QHBoxLayout(self.toolbar)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        self.btn_group = QButtonGroup(self)

        tools = [
            ("✏️ Pen", "pen"),
            ("🖌️ Highlight", "highlighter"),
            ("➡️ Arrow", "arrow"),
            ("⬜ Rect", "rect"),
            ("⭕ Circle", "circle"),
            ("① Badge", "badge"),
        ]

        for text, tool_name in tools:
            btn = QPushButton(text, self.toolbar)
            btn.setCheckable(True)
            if tool_name == "pen":
                btn.setChecked(True)
            btn.clicked.connect(lambda _, t=tool_name: self._set_tool(t))
            self.btn_group.addButton(btn)
            layout.addWidget(btn)

        # Color preset swatches
        colors = ["#EF4444", "#F59E0B", "#10B981", "#3B82F6", "#8B5CF6", "#FFFFFF"]
        for hex_code in colors:
            btn_col = QPushButton("", self.toolbar)
            btn_col.setFixedSize(22, 22)
            btn_col.setStyleSheet(
                f"background-color: {hex_code}; border-radius: 11px; border: 2px solid #2D313F;"
            )
            btn_col.clicked.connect(lambda _, c=hex_code: self._set_color(c))
            layout.addWidget(btn_col)

        # Actions
        btn_undo = QPushButton("↩️", self.toolbar)
        btn_undo.setToolTip("Undo")
        btn_undo.clicked.connect(self.undo)
        layout.addWidget(btn_undo)

        btn_clear = QPushButton("🗑️ Clear", self.toolbar)
        btn_clear.clicked.connect(self.clear_canvas)
        layout.addWidget(btn_clear)

        btn_close = QPushButton("✕ Exit", self.toolbar)
        btn_close.setStyleSheet("background-color: #EF4444; color: white;")
        btn_close.clicked.connect(self.hide)
        layout.addWidget(btn_close)

        self.toolbar.adjustSize()
        self.toolbar.move(
            (self.width() - self.toolbar.width()) // 2,
            30
        )

    def _set_tool(self, tool: str):
        self.current_tool = tool

    def _set_color(self, hex_code: str):
        self.current_color = QColor(hex_code)

    def undo(self):
        if self.items:
            self.redo_stack.append(self.items.pop())
            self.update()

    def clear_canvas(self):
        self.items.clear()
        self.redo_stack.clear()
        self.badge_counter = 1
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            # If clicked inside toolbar, let toolbar handle it
            if self.toolbar.geometry().contains(pos):
                return

            self.is_drawing = True
            self.current_points = [pos]

            if self.current_tool == "badge":
                # Instant drop badge
                item = DrawItem(
                    tool="badge",
                    color=self.current_color,
                    width=self.stroke_width,
                    points=[pos],
                    number=self.badge_counter,
                )
                self.items.append(item)
                self.badge_counter += 1
                self.is_drawing = False
                self.update()
                return

            self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            pos = event.pos()
            self.current_points.append(pos)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
            self.is_drawing = False
            if len(self.current_points) >= 2:
                item = DrawItem(
                    tool=self.current_tool,
                    color=self.current_color,
                    width=self.stroke_width,
                    points=list(self.current_points),
                )
                self.items.append(item)
            self.current_points = []
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw all committed items
        for item in self.items:
            self._render_draw_item(painter, item)

        # Draw live in-progress item
        if self.is_drawing and len(self.current_points) >= 2:
            live_item = DrawItem(
                tool=self.current_tool,
                color=self.current_color,
                width=self.stroke_width,
                points=self.current_points,
            )
            self._render_draw_item(painter, live_item)

    def _render_draw_item(self, painter: QPainter, item: DrawItem):
        if item.tool == "pen":
            pen = QPen(item.color, item.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(len(item.points) - 1):
                painter.drawLine(item.points[i], item.points[i + 1])

        elif item.tool == "highlighter":
            hl_color = QColor(item.color)
            hl_color.setAlpha(90)
            pen = QPen(hl_color, item.width * 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(len(item.points) - 1):
                painter.drawLine(item.points[i], item.points[i + 1])

        elif item.tool == "rect":
            pen = QPen(item.color, item.width, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            p1, p2 = item.points[0], item.points[-1]
            painter.drawRect(QRect(p1, p2).normalized())

        elif item.tool == "circle":
            pen = QPen(item.color, item.width, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            p1, p2 = item.points[0], item.points[-1]
            painter.drawEllipse(QRect(p1, p2).normalized())

        elif item.tool == "arrow":
            pen = QPen(item.color, item.width + 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            p1, p2 = item.points[0], item.points[-1]
            painter.drawLine(p1, p2)
            # Arrowhead calculation
            import math
            angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
            arrow_len = 18
            arrow_angle = math.pi / 6
            p_a = QPoint(
                int(p2.x() - arrow_len * math.cos(angle - arrow_angle)),
                int(p2.y() - arrow_len * math.sin(angle - arrow_angle)),
            )
            p_b = QPoint(
                int(p2.x() - arrow_len * math.cos(angle + arrow_angle)),
                int(p2.y() - arrow_len * math.sin(angle + arrow_angle)),
            )
            painter.drawLine(p2, p_a)
            painter.drawLine(p2, p_b)

        elif item.tool == "badge":
            pos = item.points[0]
            radius = 16
            painter.setBrush(QBrush(item.color))
            painter.setPen(QPen(QColor("#FFFFFF"), 2))
            painter.drawEllipse(pos, radius, radius)
            # Draw number inside
            painter.setPen(QColor("#FFFFFF"))
            font = QFont("Segoe UI", 11, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(
                QRect(pos.x() - radius, pos.y() - radius, radius * 2, radius * 2),
                Qt.AlignmentFlag.AlignCenter,
                str(item.number),
            )
