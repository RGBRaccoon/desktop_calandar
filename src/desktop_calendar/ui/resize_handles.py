from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


class ResizeHandle(QWidget):
    """DPI-independent edge drag for our frameless tool window."""

    def __init__(self, parent: QWidget, edges: Qt.Edge):
        super().__init__(parent)
        self.owner = parent
        self.edges = edges
        self.origin: QPoint | None = None
        self.initial = QRect()
        horizontal = bool(edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
        vertical = bool(edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
        if horizontal and vertical:
            cursor = (
                Qt.CursorShape.SizeFDiagCursor
                if edges
                in (Qt.Edge.TopEdge | Qt.Edge.LeftEdge, Qt.Edge.BottomEdge | Qt.Edge.RightEdge)
                else Qt.CursorShape.SizeBDiagCursor
            )
        else:
            cursor = Qt.CursorShape.SizeHorCursor if horizontal else Qt.CursorShape.SizeVerCursor
        self.setCursor(cursor)
        self.setToolTip("끌어서 크기 조절")
        self.setObjectName("resizeHandle")
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        self.origin = event.globalPosition().toPoint()
        self.initial = self.owner.geometry()
        self.owner.setProperty("resizing", True)
        self.owner.raise_()
        self.owner.activateWindow()
        self.grabMouse()
        event.accept()

    def mouseMoveEvent(self, event):
        if self.origin is None:
            return
        delta = event.globalPosition().toPoint() - self.origin
        rect = QRect(self.initial)
        minimum = self.owner.minimumSize().expandedTo(self.owner.minimumSizeHint())
        if self.edges & Qt.Edge.LeftEdge:
            rect.setLeft(
                min(self.initial.left() + delta.x(), self.initial.right() - minimum.width() + 1)
            )
        if self.edges & Qt.Edge.RightEdge:
            rect.setRight(
                max(self.initial.right() + delta.x(), self.initial.left() + minimum.width() - 1)
            )
        if self.edges & Qt.Edge.TopEdge:
            rect.setTop(
                min(self.initial.top() + delta.y(), self.initial.bottom() - minimum.height() + 1)
            )
        if self.edges & Qt.Edge.BottomEdge:
            rect.setBottom(
                max(self.initial.bottom() + delta.y(), self.initial.top() + minimum.height() - 1)
            )
        self.owner.setGeometry(rect)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.origin is not None:
            # Geometry already follows move events. Release coordinates may use a moved handle.
            self.origin = None
            self.owner.setProperty("resizing", False)
            self.releaseMouse()
            event.accept()

    def paintEvent(self, event):
        if self.edges == Qt.Edge.BottomEdge | Qt.Edge.RightEdge:
            painter = QPainter(self)
            painter.setPen(QColor("#8e9eb4"))
            for offset in (5, 10, 15):
                painter.drawLine(
                    self.width() - offset,
                    self.height() - 3,
                    self.width() - 3,
                    self.height() - offset,
                )


class ResizeHandles:
    BORDER = 10
    CORNER = 22

    def __init__(self, owner: QWidget):
        self.owner = owner
        edge = Qt.Edge
        self.handles = [
            ResizeHandle(owner, edges)
            for edges in (
                edge.TopEdge,
                edge.BottomEdge,
                edge.LeftEdge,
                edge.RightEdge,
                edge.TopEdge | edge.LeftEdge,
                edge.TopEdge | edge.RightEdge,
                edge.BottomEdge | edge.LeftEdge,
                edge.BottomEdge | edge.RightEdge,
            )
        ]
        self.update()

    def update(self):
        w, h, b, c = self.owner.width(), self.owner.height(), self.BORDER, self.CORNER
        rectangles = [
            (c, 0, w - 2 * c, b),
            (c, h - b, w - 2 * c, b),
            (0, c, b, h - 2 * c),
            (w - b, c, b, h - 2 * c),
            (0, 0, c, c),
            (w - c, 0, c, c),
            (0, h - c, c, c),
            (w - c, h - c, c, c),
        ]
        for handle, rect in zip(self.handles, rectangles, strict=True):
            handle.setGeometry(*rect)
            handle.raise_()
