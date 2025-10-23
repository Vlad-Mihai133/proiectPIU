import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QTableWidget, QTableWidgetItem, QInputDialog
)
from PySide6.QtCore import Qt, QMimeData, QPoint
from PySide6.QtGui import QDrag, QMouseEvent, QColor


class ScheduleTable(QTableWidget):
    def __init__(self, rows, cols):
        super().__init__(rows, cols)
        self.dragStartPosition = None
        self.setAcceptDrops(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setDragDropMode(QTableWidget.DragDropMode.InternalMove)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(True)

        # Configurare tabel
        for row in range(rows):
            self.setRowHeight(row, 40)
        for col in range(cols):
            self.setColumnWidth(col, 120)

        self.setHorizontalHeaderLabels(["Monday", "Tuesday", "Wednesday",
                                        "Thursday", "Friday", "Saturday", "Sunday"])
        self.setVerticalHeaderLabels([f"{h}:00" for h in range(0, 24)])

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragStartPosition = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Porneste drag-ul manual cand utilizatorul trage de o celula.
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.dragStartPosition:
            return
        if (event.pos() - self.dragStartPosition).manhattanLength() < QApplication.startDragDistance():
            return

        item = self.itemAt(self.dragStartPosition)
        if item is None:
            return

        drag = QDrag(self)
        mimeData = QMimeData()
        mimeData.setText(item.text())
        mimeData.setColorData(item.background().color())
        drag.setMimeData(mimeData)

        result = drag.exec_(Qt.MoveAction)

        if result == Qt.MoveAction:
            self.takeItem(self.row(item), self.column(item))

    def mouseDoubleClickEvent(self, event):
        # Adauga un eveniment prin dublu click.
        item = self.itemAt(event.pos())
        row = self.rowAt(event.pos().y())
        col = self.columnAt(event.pos().x())
        if row < 0 or col < 0:
            return

        if item is None:
            text, ok = QInputDialog.getText(self, "Add Event", "Event name:")
            if ok and text.strip():
                new_item = QTableWidgetItem(text.strip())
                new_item.setTextAlignment(Qt.AlignCenter)
                new_item.setBackground(Qt.yellow)
                self.setItem(row, col, new_item)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        """Mută evenimentul în altă celulă."""
        pos = event.position().toPoint()
        row = self.rowAt(pos.y())
        col = self.columnAt(pos.x())
        if row < 0 or col < 0:
            return

        text = event.mimeData().text()
        color = event.mimeData().colorData()
        if text:
            new_item = QTableWidgetItem(text)
            new_item.setTextAlignment(Qt.AlignCenter)
            new_item.setBackground(color if color else Qt.yellow)
            self.setItem(row, col, new_item)

        event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calendar")
        self.setFixedSize(920, 700)
        self.setStyleSheet("background-color: #f5f5f5;")

        central_widget = QWidget()
        layout = QHBoxLayout(central_widget)

        self.schedule_table = ScheduleTable(24, 7)
        layout.addWidget(self.schedule_table)

        self.setCentralWidget(central_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
