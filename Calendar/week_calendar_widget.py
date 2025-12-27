from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush

from schedule_table import ScheduleTable
from models import CalendarEvent


class WeekCalendarWidget(QWidget):
    """
    Widget care afiseaza un ScheduleTable pentru o saptamana si pastreaza
    evenimentele pentru toate saptamanile (events_by_date).
    """

    def __init__(self, parent=None, start_monday: date | None = None):
        super().__init__(parent)

        self.current_monday: date = self._ensure_monday(start_monday or date.today())

        # Store global: cheie = "YYYY-MM-DD", valoare = lista de dict-uri de event
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

        # initializeaza header + incarcare evenimente pentru saptamana curenta
        self._update_headers_and_label()
        self._load_current_week()

    # ---------------- helpers interne ----------------

    def _ensure_monday(self, any_day: date) -> date:
        """Returneaza luni din saptamana care contine any_day."""
        return any_day - timedelta(days=any_day.weekday())

    def _week_dates(self) -> list[date]:
        """Returneaza lista cu cele 7 date din saptamana curenta (luni-duminica)."""
        return [self.current_monday + timedelta(days=i) for i in range(7)]

    def _update_headers_and_label(self):
        """Actualizeaza header-ul tabelului si label-ul cu intervalul saptamanii curente."""
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
        self._update_disabled_columns()

    # ---------------- store <-> tabel ----------------

    def _store_current_week(self):
        """
        Copiaza evenimentele din tabel in store-ul global (events_by_date)
        pentru cele 7 zile ale saptamanii curente.
        Salveaza DOAR evenimentele de baza (nu si aparitiile generate).
        """
        # stergem evenimentele baza pentru zilele acestei saptamani
        for d in self._week_dates():
            self.events_by_date.pop(d.isoformat(), None)

        # re-adaugam evenimentele de baza din tabel
        for (row, col), ev in self.table.events_by_pos.items():
            # Sarim peste aparitiile generate de recurenta
            if ev.is_generated:
                continue

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
                "repeat_count": ev.repeat_count,
                "repeat_forever": ev.repeat_forever,
            })

    def _load_current_week(self):
        """
        Reincarca in tabel evenimentele pentru saptamana curenta, inclusiv recurentele.
        """
        self.table.reset_table()
        week_days = self._week_dates()  # list[date]

        for base_date_str, events in self.events_by_date.items():
            base_date = date.fromisoformat(base_date_str)

            for ev_dict in events:
                title = ev_dict.get("title", "")
                hour = ev_dict.get("hour", 0)
                duration = ev_dict.get("duration", 1)
                color_tuple = ev_dict.get("color", (255, 255, 0))
                description = ev_dict.get("description", "")
                locked = ev_dict.get("locked", False)
                repeat_count = max(1, ev_dict.get("repeat_count", 1))
                repeat_forever = ev_dict.get("repeat_forever", False)

                color = QColor(*color_tuple)
                brush = QBrush(color)

                for col_idx, current_date in enumerate(week_days):
                    diff_days = (current_date - base_date).days
                    if diff_days < 0:
                        continue
                    if diff_days % 7 != 0:
                        continue

                    k = diff_days // 7  # a cata aparitie (0 = event de baza in saptamana sa)
                    if k == 0:
                        if repeat_count < 1 and not repeat_forever:
                            continue
                    else:
                        if not repeat_forever and k >= repeat_count:
                            continue  # in afara numarului de repetari

                    is_generated = (k > 0)

                    item = QTableWidgetItem(title)
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setBackground(brush)
                    item.setData(Qt.BackgroundRole, brush)

                    self.table.setItem(hour, col_idx, item)
                    self.table.setSpan(hour, col_idx, duration, 1)

                    ev = CalendarEvent(
                        title=title,
                        start_row=hour,
                        day_col=col_idx,
                        duration=duration,
                        color=color,
                        description=description,
                        locked=locked,
                        repeat_count=repeat_count,
                        repeat_forever=repeat_forever,
                        is_generated=is_generated,
                    )
                    self.table.events_by_pos[(hour, col_idx)] = ev

        self.table.viewport().update()

    # ---------------- navigare saptamani ----------------

    def _go_prev_week(self):
        """Navigheaza la saptamana anterioara, pastrand evenimentele in store."""
        self._store_current_week()
        self.current_monday -= timedelta(days=7)
        self._update_headers_and_label()
        self._load_current_week()

    def _go_next_week(self):
        """Navigheaza la saptamana urmatoare, pastrand evenimentele in store."""
        self._store_current_week()
        self.current_monday += timedelta(days=7)
        self._update_headers_and_label()
        self._load_current_week()

    # ---------------- serializare globala pentru Save/Load ----------------

    def export_all_events(self) -> dict:
        """
        Returneaza un dict serializabil JSON cu toate evenimentele
        (pentru toate saptamanile/lunile).
        """
        # mai intai salvam ce e in saptamana curenta in store
        self._store_current_week()

        all_events: list[dict] = []
        for dstr, events in self.events_by_date.items():
            for ev in events:
                ev_copy = ev.copy()
                ev_copy["date"] = dstr  # adaugam cheia de data
                all_events.append(ev_copy)

        return {"events": all_events}

    def load_all_events(self, data: dict):
        """
        Reincarca toate evenimentele dintr-un dict JSON (formatul export_all_events)
        si afiseaza doar saptamana curenta.
        """
        self.events_by_date.clear()

        for ev in data.get("events", []):
            dstr = ev.get("date")
            if not dstr:
                continue
            ev_copy = {
                "title": ev.get("title", ""),
                "hour": ev.get("hour", 0),
                "duration": ev.get("duration", 1),
                "color": tuple(ev.get("color", (255, 255, 0))),
                "description": ev.get("description", ""),
                "locked": ev.get("locked", False),
                "repeat_count": max(1, ev.get("repeat_count", 1)),
                "repeat_forever": ev.get("repeat_forever", False),
            }
            day_events = self.events_by_date.setdefault(dstr, [])
            day_events.append(ev_copy)

        # re-desenam saptamana curenta
        self._update_headers_and_label()
        self._load_current_week()

    def _update_disabled_columns(self):
        """Calculeaza ce zile din saptamana curenta sunt in trecut si le dezactiveaza in tabel."""
        today = date.today()
        days = self._week_dates()

        disabled_cols: list[int] = []

        week_start = days[0]
        week_end = days[-1]

        if week_end < today:
            # saptamana complet in trecut -> toate cele 7 zile dezactivate
            disabled_cols = list(range(7))
        elif week_start > today:
            # saptamana complet in viitor -> nimic dezactivat
            disabled_cols = []
        else:
            # saptamana curenta -> dezactivam doar zilele STRICT inainte de azi
            for idx, d in enumerate(days):
                if d < today:
                    disabled_cols.append(idx)

        self.table.set_disabled_columns(disabled_cols)