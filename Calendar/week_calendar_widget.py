from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush

from schedule_table import ScheduleTable
from models import CalendarEvent


class WeekCalendarWidget(QWidget):
    """
    Widget care afișează un ScheduleTable pentru o săptămână și păstrează
    evenimentele pentru toate săptămânile (events_by_date).
    """

    def __init__(self, parent=None, start_monday: date | None = None):
        super().__init__(parent)

        self.current_monday: date = self._ensure_monday(start_monday or date.today())

        # Store global: cheie = "YYYY-MM-DD", valoare = listă de dict-uri de event
        # dict-urile au schema: {
        #     "title", "hour", "duration", "color": (r,g,b),
        #     "description", "locked"
        # }
        self.events_by_date: dict[str, list[dict]] = {}

        self.table = ScheduleTable(rows=24, cols=7)

        # -------- header navigare --------
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)

        self.prev_btn = QPushButton("◀ Prev week")
        self.next_btn = QPushButton("Next week ▶")
        self.week_label = QLabel()
        self.week_label.setObjectName("WeekLabel")
        self.week_label.setAlignment(Qt.AlignCenter)

        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.week_label, stretch=1)
        nav_layout.addWidget(self.next_btn)

        # -------- layout principal --------
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(nav_layout)
        main_layout.addWidget(self.table)

        # semnale
        self.prev_btn.clicked.connect(self._go_prev_week)
        self.next_btn.clicked.connect(self._go_next_week)

        # inițializează header + încărcare evenimente pentru săptămâna curentă
        self._update_headers_and_label()
        self._load_current_week()

    # ---------------- helpers interne ----------------

    def _ensure_monday(self, any_day: date) -> date:
        """Returnează luni din săptămâna care conține any_day."""
        return any_day - timedelta(days=any_day.weekday())

    def _week_dates(self) -> list[date]:
        """Returnează lista cu cele 7 date din săptămâna curentă (luni-duminică)."""
        return [self.current_monday + timedelta(days=i) for i in range(7)]

    def _update_headers_and_label(self):
        """Actualizează header-ul tabelului și label-ul cu intervalul săptămânii curente."""
        day_labels: list[str] = []
        for d in self._week_dates():
            day_name = d.strftime("%a")  # Mon, Tue, ...
            day_label = f"{day_name}\n{d.day:02d}/{d.month:02d}"
            day_labels.append(day_label)

        self.table.set_day_labels(day_labels)

        week_end = self.current_monday + timedelta(days=6)
        self.week_label.setText(
            f"Week: {self.current_monday.strftime('%d %b %Y')} - {week_end.strftime('%d %b %Y')}"
        )

    # ---------------- store <-> tabel ----------------

    def _store_current_week(self):
        """
        Copiază evenimentele din tabel în store-ul global (events_by_date)
        pentru cele 7 zile ale săptămânii curente.
        """
        # 1. ștergem din store toate evenimentele pentru zilele acestei săptămâni
        for d in self._week_dates():
            self.events_by_date.pop(d.isoformat(), None)

        # 2. re-adăugăm din tabel evenimentele actuale ale săptămânii
        for (row, col), ev in self.table.events_by_pos.items():
            # col = 0..6 => offset față de current_monday
            ev_date = self.current_monday + timedelta(days=ev.day_col)
            dstr = ev_date.isoformat()

            color_tuple = (ev.color.red(), ev.color.green(), ev.color.blue())

            day_events = self.events_by_date.setdefault(dstr, [])
            day_events.append({
                "title": ev.title,
                "hour": ev.start_row,
                "duration": ev.duration,
                "color": color_tuple,
                "description": ev.description,
                "locked": ev.locked,
            })

    def _load_current_week(self):
        """
        Reîncarcă în tabel doar evenimentele pentru săptămâna curentă din store-ul global.
        """
        self.table.reset_table()

        for d_idx, current_date in enumerate(self._week_dates()):
            dstr = current_date.isoformat()
            events = self.events_by_date.get(dstr, [])
            for ev_dict in events:
                title = ev_dict.get("title", "")
                start_row = ev_dict.get("hour", 0)
                duration = ev_dict.get("duration", 1)
                color_tuple = ev_dict.get("color", (255, 255, 0))
                description = ev_dict.get("description", "")
                locked = ev_dict.get("locked", False)

                color = QColor(*color_tuple)
                brush = QBrush(color)

                item = QTableWidgetItem(title)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(brush)
                item.setData(Qt.BackgroundRole, brush)

                self.table.setItem(start_row, d_idx, item)
                self.table.setSpan(start_row, d_idx, duration, 1)

                ev = CalendarEvent(
                    title=title,
                    start_row=start_row,
                    day_col=d_idx,
                    duration=duration,
                    color=color,
                    description=description,
                    locked=locked
                )
                self.table.events_by_pos[(start_row, d_idx)] = ev

        self.table.viewport().update()

    # ---------------- navigare săptămâni ----------------

    def _go_prev_week(self):
        """Navighează la săptămâna anterioară, păstrând evenimentele în store."""
        self._store_current_week()
        self.current_monday -= timedelta(days=7)
        self._update_headers_and_label()
        self._load_current_week()

    def _go_next_week(self):
        """Navighează la săptămâna următoare, păstrând evenimentele în store."""
        self._store_current_week()
        self.current_monday += timedelta(days=7)
        self._update_headers_and_label()
        self._load_current_week()

    # ---------------- serializare globală pentru Save/Load ----------------

    def export_all_events(self) -> dict:
        """
        Returnează un dict serializabil JSON cu toate evenimentele
        (pentru toate săptămânile/lunile).
        """
        # mai întâi salvăm ce e în săptămâna curentă în store
        self._store_current_week()

        all_events: list[dict] = []
        for dstr, events in self.events_by_date.items():
            for ev in events:
                ev_copy = ev.copy()
                ev_copy["date"] = dstr  # adăugăm cheia de dată
                all_events.append(ev_copy)

        return {"events": all_events}

    def load_all_events(self, data: dict):
        """
        Reîncarcă toate evenimentele dintr-un dict JSON (formatul export_all_events)
        și afișează doar săptămâna curentă.
        """
        self.events_by_date.clear()

        for ev in data.get("events", []):
            dstr = ev.get("date")
            if not dstr:
                continue
            # copiem fără cheia "date"
            ev_copy = {
                "title": ev.get("title", ""),
                "hour": ev.get("hour", 0),
                "duration": ev.get("duration", 1),
                "color": tuple(ev.get("color", (255, 255, 0))),
                "description": ev.get("description", ""),
                "locked": ev.get("locked", False),
            }
            day_events = self.events_by_date.setdefault(dstr, [])
            day_events.append(ev_copy)

        # re-desenăm săptămâna curentă
        self._update_headers_and_label()
        self._load_current_week()
