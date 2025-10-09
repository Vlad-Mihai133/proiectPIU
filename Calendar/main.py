import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem
)
from PySide6.QtCore import Qt, QMimeData, QPoint
from PySide6.QtGui import QDrag, QMouseEvent, QColor


class TaskList(QListWidget):

    def __init__(self):
        super().__init__()
        self.dragStartPosition = None
        self.setDragEnabled(True)
        tasks = {
            "Maths": "#FFD966",
            "Physics": "#9FC5E8",
            "Computer Science": "#B6D7A8",
            "Physical Education": "#F4CCCC",
            "Biology": "#D9D2E9"
        }

        for name, color in tasks.items():
            item = QListWidgetItem(name)
            item.setBackground(QColor(color))
            item.setTextAlignment(Qt.AlignCenter)
            self.addItem(item)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragStartPosition = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() == Qt.LeftButton):
            return
        if ((event.pos() - self.dragStartPosition).manhattanLength()
                < QApplication.startDragDistance()):
            return
        item = self.currentItem()
        if item is None:
            return

        drag = QDrag(self)
        mimeData = QMimeData()
        mimeData.setText(item.text())
        mimeData.setColorData(item.background().color())
        drag.setMimeData(mimeData)
        drag.exec_(Qt.MoveAction)


class ScheduleTable(QTableWidget):
    def __init__(self, rows, cols):
        super().__init__(rows, cols)
        self.setAcceptDrops(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        pos = event.position().toPoint()
        row = self.rowAt(pos.y())
        col = self.columnAt(pos.x())
        if row >= 0 and col >= 0:
            text = event.mimeData().text()
            color = event.mimeData().colorData()

            new_item = QTableWidgetItem(text)
            new_item.setTextAlignment(Qt.AlignCenter)

            if color:
                new_item.setBackground(color)

            self.setItem(row, col, new_item)
            event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

        # Default size and position
        self.setWindowTitle("Calendar")
        self.setFixedSize(1050, 700)
        self.move(
            QApplication.primaryScreen().availableGeometry().center() - self.rect().center()
        )
        self.setStyleSheet("background-color: #f5f5f5;")

        central_widget = QWidget()
        layout = QHBoxLayout(central_widget)

        # Lista de taskuri
        self.task_list = TaskList()
        layout.addWidget(self.task_list, 1)

        # Folosim clasa ScheduleTable
        self.schedule_table = ScheduleTable(24, 7)
        self.schedule_table.setHorizontalHeaderLabels(["Monday", "Tuesday", "Wednesday",
                                                       "Thursday", "Friday", "Saturday", "Sunday"])
        self.schedule_table.setVerticalHeaderLabels([f"{h}:00" for h in range(0, 24)])
        layout.addWidget(self.schedule_table, 2)

        self.setCentralWidget(central_widget)

    def dragEnterEvent(self, e):
        e.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
