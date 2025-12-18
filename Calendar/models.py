from PySide6.QtGui import QColor
from dataclasses import dataclass

@dataclass
class CalendarEvent:
    """Reprezintă un eveniment din calendar."""
    title: str
    start_row: int
    day_col: int
    duration: int  # în ore (număr de rânduri)
    color: QColor
    description: str = ""
    locked: bool = False
    repeat_count: int = 1
    repeat_forever: bool = False
    is_generated: bool = False

    @property
    def start_hour(self) -> int:
        """Ora de start (egală cu start_row)."""
        return self.start_row

    @property
    def end_hour(self) -> int:
        """Ora de final (start_row + duration)."""
        return self.start_row + self.duration

    @property
    def day_index(self) -> int:
        """Indexul zilei (coloana din tabel)."""
        return self.day_col