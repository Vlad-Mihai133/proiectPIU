import json

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QToolBar,
    QFileDialog,
)
from PySide6.QtGui import QAction
from schedule_table import ScheduleTable
from week_calendar_widget import WeekCalendarWidget
from theme import APP_DARK_STYLE


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calendar")
        self.setFixedSize(920, 700)
        self.setStyleSheet(APP_DARK_STYLE)

        central_widget = QWidget()
        layout = QHBoxLayout(central_widget)

        self.week_calendar = WeekCalendarWidget(self)
        layout.addWidget(self.week_calendar)

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
            self, "Salveaza orarul", "", "JSON Files (*.json)"
        )
        if file_path:
            state = self.week_calendar.export_all_events()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)

    def load_schedule(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Incarca orarul", "", "JSON Files (*.json)"
        )
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.week_calendar.load_all_events(data)
