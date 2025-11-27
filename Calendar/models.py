from dataclasses import dataclass
from PySide6.QtGui import QColor


@dataclass
class CalendarEvent:
    title: str
    start_row: int
    day_col: int
    duration: int  # în ore (număr de rânduri)
    color: QColor
    description: str = ""
