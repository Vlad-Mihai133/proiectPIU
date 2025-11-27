from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QToolBar,
    QFileDialog,
)
from PySide6.QtGui import QAction
from schedule_table import ScheduleTable


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

        toolbar = QToolBar("File")
        self.addToolBar(toolbar)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_schedule)
        toolbar.addAction(save_action)

        load_action = QAction("Load", self)
        load_action.triggered.connect(self.load_schedule)
        toolbar.addAction(load_action)

    def save_schedule(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Salvează orarul", "", "JSON Files (*.json)"
        )
        if file_path:
            self.schedule_table.save_to_json(file_path)

    def load_schedule(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Încarcă orarul", "", "JSON Files (*.json)"
        )
        if file_path:
            self.schedule_table.load_from_json(file_path)
