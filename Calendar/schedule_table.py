import json
from typing import Dict, Tuple, Optional

from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QInputDialog,
    QMessageBox,
    QApplication, QDialog,
)
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDrag, QMouseEvent, QColor

from models import CalendarEvent
from event_dialog import EventEditDialog

class ScheduleTable(QTableWidget):
    def __init__(self, rows: int, cols: int):
        """Initializează tabelul de program și modelul intern de evenimente."""
        super().__init__(rows, cols)
        self.dragStartPosition: Optional[Qt.QPoint] = None
        self.setAcceptDrops(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setDragDropMode(QTableWidget.DragDropMode.InternalMove)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(True)

        self.setMouseTracking(True)
        self._resize_active = False
        self._resize_edge = None
        self._resize_anchor_row = None
        self._resize_col = None
        self._resize_margin_px = 6
        self._span_top_row = None
        self._span_len = 1
        self._last_drop_target = None
        self.disabled_cols: set[int] = set()


        self.events_by_pos: Dict[Tuple[int, int], CalendarEvent] = {}
        self._dragging_src: Optional[Tuple[int, int]] = None

        for row in range(rows):
            self.setRowHeight(row, 40)
        for col in range(cols):
            self.setColumnWidth(col, 120)

        self.setHorizontalHeaderLabels([
            "Monday", "Tuesday", "Wednesday",
            "Thursday", "Friday", "Saturday", "Sunday"
        ])
        self.setVerticalHeaderLabels([f"{h}:00" for h in range(0, 24)])

    # ===================== Interacțiuni mouse / drag =====================

    def mousePressEvent(self, event: QMouseEvent):
        """Gestionează apăsarea mouse-ului: pregătește resize sau drag pentru un eveniment."""
        if event.button() == Qt.MouseButton.LeftButton:
            posf = event.position()
            p = posf.toPoint()
            item = self.itemAt(p)
            if item is not None:
                col = self.column(item)
                if col in self.disabled_cols:
                    return
                y = posf.y()
                near_top, near_bottom = self._is_near_vertical_edge(item, y)
                if near_top or near_bottom:
                    self._begin_resize(item, 'top' if near_top else 'bottom')
                    return
            self.dragStartPosition = p
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Gestionează mișcarea mouse-ului: actualizează resize sau pornește drag-ul unui eveniment."""
        if self._resize_active:
            self._update_resize(self.rowAt(event.position().toPoint().y()))
            return

        posf = event.position()
        p = posf.toPoint()
        item = self.itemAt(p)
        if item is not None:
            self._update_edge_cursor(item, posf.y())
        else:
            self.viewport().unsetCursor()

        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.dragStartPosition:
            return
        if (p - self.dragStartPosition).manhattanLength() < QApplication.startDragDistance():
            return

        item = self.itemAt(self.dragStartPosition)
        if item is None:
            return

        src_row = self.row(item)
        src_col = self.column(item)
        ev = self.events_by_pos.get((src_row, src_col))
        if ev is not None and ev.locked:
            # evenimentul este locked -> nu permitem drag
            return

        span_len = max(1, self.rowSpan(src_row, src_col))

        self._dragging_src = (src_row, src_col)

        drag = QDrag(self)
        mimeData = QMimeData()
        mimeData.setText(f"{span_len}|{item.text()}")
        mimeData.setColorData(item.background().color())
        drag.setMimeData(mimeData)

        result = drag.exec(Qt.MoveAction)
        if result == Qt.MoveAction:
            if self._last_drop_target is not None and self._last_drop_target != (src_row, src_col):
                self.setSpan(src_row, src_col, 1, 1)
                self.takeItem(src_row, src_col)
            self._last_drop_target = None
            self._dragging_src = None

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Încheie operațiunile de resize la eliberarea butonului de mouse."""
        if event.button() == Qt.MouseButton.LeftButton and self._resize_active:
            self._end_resize()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Deschide un dialog pentru a crea sau edita un eveniment (nume + descriere + locked)."""
        posf = event.position()
        p = posf.toPoint()

        row = self.rowAt(p.y())
        col = self.columnAt(p.x())
        if row < 0 or col < 0:
            return

        if col in self.disabled_cols:
            return

        # Găsim evenimentul care acoperă (row, col), chiar dacă userul a dat click pe mijlocul span-ului
        existing_ev = None
        top_row = row

        direct_ev = self.events_by_pos.get((row, col))
        if direct_ev is not None:
            existing_ev = direct_ev
            top_row = direct_ev.start_row
        else:
            for (srow, scol), ev in self.events_by_pos.items():
                if scol != col:
                    continue
                if srow <= row < srow + ev.duration:
                    existing_ev = ev
                    top_row = srow
                    break

        item = self.item(top_row, col)

        # numele zilelor, în aceeași ordine ca header-ul tabelului
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        if existing_ev is not None and item is not None:
            # EDITARE eveniment existent
            start_hour = existing_ev.start_hour
            end_hour = existing_ev.end_hour
            day_name = day_names[existing_ev.day_index] if 0 <= existing_ev.day_index < len(
                day_names) else f"Day {existing_ev.day_index}"
            time_info = f"{day_name}, {start_hour:02d}:00 - {end_hour:02d}:00"

            dlg = EventEditDialog(
                title=existing_ev.title,
                description=existing_ev.description,
                locked=existing_ev.locked,
                time_info=time_info,
                parent=self
            )
            dlg.repeat_spin.setValue(existing_ev.repeat_count or 1)
            dlg.repeat_forever_check.setChecked(existing_ev.repeat_forever)
            if existing_ev.repeat_forever:
                dlg.repeat_spin.setEnabled(False)

            if dlg.exec() == QDialog.Accepted:
                new_title, new_desc, new_locked, repeat_count, repeat_forever = dlg.get_values()
                if new_title:
                    existing_ev.title = new_title
                    existing_ev.description = new_desc
                    existing_ev.locked = new_locked
                    existing_ev.repeat_count = repeat_count
                    existing_ev.repeat_forever = repeat_forever
                    item.setText(new_title)
            return

        # CREARE eveniment nou
        day_name = day_names[col] if 0 <= col < len(day_names) else f"Day {col}"
        start_hour = row
        end_hour = row + 1
        time_info = f"{day_name}, {start_hour:02d}:00 - {end_hour:02d}:00"

        dlg = EventEditDialog(time_info=time_info, parent=self)
        if dlg.exec() == QDialog.Accepted:
            new_title, new_desc, new_locked, repeat_count, repeat_forever = dlg.get_values()
            if not new_title:
                return

            import random
            new_item = QTableWidgetItem(new_title)
            new_item.setTextAlignment(Qt.AlignCenter)
            random_color = QColor(
                random.randint(100, 255),
                random.randint(100, 255),
                random.randint(100, 255)
            )
            new_item.setBackground(random_color)
            self.setItem(row, col, new_item)

            self.events_by_pos[(row, col)] = CalendarEvent(
                title=new_title,
                start_row=row,
                day_col=col,
                duration=1,
                color=random_color,
                description=new_desc,
                locked=new_locked,
                repeat_count=repeat_count,
                repeat_forever=repeat_forever,
            )

    # ===================== Drag & drop =====================

    def dragEnterEvent(self, event):
        """Acceptă intrarea unui drag în tabel."""
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Acceptă mișcarea unui drag deasupra tabelului."""
        event.acceptProposedAction()

    def dropEvent(self, event):
        """Gestionează logica de drop: mutare eveniment existent sau creare nou eveniment și rezolvarea conflictelor."""
        pos = event.position().toPoint()
        row = self.rowAt(pos.y())
        col = self.columnAt(pos.x())


        if not self._constraint_inside_window(row, col):
            self._last_drop_target = None
            event.ignore()
            return

        if col in self.disabled_cols:
            event.ignore()
            return

        raw_text = event.mimeData().text() or ""
        if "|" in raw_text:
            try:
                span_str, text = raw_text.split("|", 1)
                span_len = max(1, int(span_str))
            except ValueError:
                text = raw_text
                span_len = 1
        else:
            text = raw_text
            span_len = 1

        color = event.mimeData().colorData()

        original_ev = None
        if self._dragging_src is not None:
            src_row, src_col = self._dragging_src
            original_ev = self.events_by_pos.get((src_row, src_col))

        if original_ev is not None:
            """Mută un eveniment existent, ajustând doar evenimentele cu care intră în conflict."""
            if original_ev.locked:
                QMessageBox.information(self, "Locked event", "This event is locked and cannot be moved.")
                event.ignore()
                return

            # CONSTRÂNGERE 1: nu schimbăm ziua
            col = self._constraint_same_day_column(original_ev, col)

            # CONSTRÂNGERE 2: evenimentul rămâne în zi
            duration = original_ev.duration
            row, duration = self._constraint_within_day(row, duration)

            if row + duration > self.rowCount():
                row = max(0, self.rowCount() - duration)

            new_start = row
            new_end = row + duration - 1

            conflicts = []
            for (erow, ecol), ev in list(self.events_by_pos.items()):
                if ev is original_ev:
                    continue
                if ecol != col:
                    continue
                ev_start = ev.start_row
                ev_end = ev.start_row + ev.duration - 1
                if self._intervals_overlap(new_start, new_end, ev_start, ev_end):
                    conflicts.append(ev)

            locked_conflicts = [ev for ev in conflicts if getattr(ev, "locked", False)]
            if locked_conflicts:
                QMessageBox.warning(
                    self,
                    "Locked conflict",
                    "You cannot place an event over a locked event."
                )
                event.ignore()
                return

            if conflicts:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Conflict detected")
                msg.setText(
                    f"Event '{original_ev.title}' overlaps with {len(conflicts)} event(s).\nApply shrink adjustment?"
                )
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.button(QMessageBox.Yes).setText("Yes, adjust")
                msg.button(QMessageBox.No).setText("No, cancel")
                choice = msg.exec()

                if choice == QMessageBox.No:
                    event.ignore()
                    return

                for overlapped in conflicts:
                    ev_start = overlapped.start_row
                    ev_end = overlapped.start_row + overlapped.duration - 1

                    if new_start > ev_start and new_end < ev_end:
                        self._split_event_middle(overlapped, new_start, new_end)
                    elif new_start <= ev_start <= new_end < ev_end:
                        cut = new_end - ev_start + 1
                        self._shrink_event_from_top(overlapped, cut)
                    elif ev_start < new_start <= ev_end <= new_end:
                        cut = ev_end - new_start + 1
                        self._shrink_event_by(overlapped, cut)
                    elif new_start <= ev_start and new_end >= ev_end:
                        self.setSpan(ev_start, overlapped.day_col, 1, 1)
                        self.takeItem(ev_start, overlapped.day_col)
                        self.events_by_pos.pop((ev_start, overlapped.day_col), None)

            old_start = original_ev.start_row
            old_col = original_ev.day_col

            item = self.item(old_start, old_col)
            if item is not None:
                self.setSpan(old_start, old_col, 1, 1)
                self.takeItem(old_start, old_col)

                self.setItem(new_start, col, item)
                self.setSpan(new_start, col, duration, 1)

            self.events_by_pos.pop((old_start, old_col), None)
            original_ev.start_row = new_start
            original_ev.day_col = col
            original_ev.duration = duration
            self.events_by_pos[(new_start, col)] = original_ev

            self._last_drop_target = (new_start, col)
            self._dragging_src = None
            event.acceptProposedAction()
            return

        """Creează sau plasează un eveniment nou, ajustând evenimentele existente dacă se suprapune."""
        row, span_len = self._constraint_within_day(row, span_len)

        overlaps = self._find_overlaps(row, span_len, col)

        locked_overlaps = [ev for ev in overlaps if getattr(ev, "locked", False)]
        if locked_overlaps:
            QMessageBox.warning(
                self,
                "Locked conflict",
                "You cannot place an event over a locked event."
            )
            event.ignore()
            return

        if overlaps:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Conflict detected")
            msg.setText(
                f"Event '{text}' overlaps with {len(overlaps)} event(s).\nApply shrink adjustment?"
            )
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.button(QMessageBox.Yes).setText("Yes, adjust")
            msg.button(QMessageBox.No).setText("No, cancel")
            choice = msg.exec()

            if choice == QMessageBox.No:
                event.ignore()
                return

            new_start = row
            new_end = row + max(1, span_len) - 1
            for overlapped in overlaps:
                ev_start = overlapped.start_row
                ev_end = overlapped.start_row + overlapped.duration - 1

                if new_start > ev_start and new_end < ev_end:
                    self._split_event_middle(overlapped, new_start, new_end)
                elif new_start <= ev_start <= new_end < ev_end:
                    cut = new_end - ev_start + 1
                    self._shrink_event_from_top(overlapped, cut)
                elif ev_start < new_start <= ev_end <= new_end:
                    cut = ev_end - new_start + 1
                    self._shrink_event_by(overlapped, cut)
                elif new_start <= ev_start and new_end >= ev_end:
                    self.setSpan(ev_start, overlapped.day_col, 1, 1)
                    self.takeItem(ev_start, overlapped.day_col)
                    self.events_by_pos.pop((ev_start, overlapped.day_col), None)

        self._last_drop_target = (row, col)

        if text:
            new_item = QTableWidgetItem(text)
            new_item.setTextAlignment(Qt.AlignCenter)
            new_item.setBackground(color if color else Qt.yellow)
            self.setItem(row, col, new_item)
            self.setSpan(row, col, span_len, 1)

        ev = CalendarEvent(
            title=text,
            start_row=row,
            day_col=col,
            duration=span_len,
            color=color if color else QColor(Qt.yellow)
        )
        self.events_by_pos[(row, col)] = ev
        event.acceptProposedAction()

    # ===================== Resize logic =====================

    def _is_near_vertical_edge(self, item: QTableWidgetItem, y: float):
        """Verifică dacă poziția y este aproape de marginea verticală a unui item (sus sau jos)."""
        rect = self.visualItemRect(item)
        return (
            abs(y - rect.top()) <= self._resize_margin_px,
            abs(y - rect.bottom()) <= self._resize_margin_px
        )

    def _begin_resize(self, item: QTableWidgetItem, edge: str):
        """Pornește modul de resize pentru un eveniment, dacă nu este locked."""
        row = self.row(item)
        col = self.column(item)

        ev = self.events_by_pos.get((row, col))
        if ev is not None and ev.locked:
            # evenimentul e locked -> nu permitem resize
            return

        if col in self.disabled_cols:
            return

        self._resize_active = True
        self._resize_edge = edge
        span = max(1, self.rowSpan(row, col))
        top_row = row
        bottom_row = row + span - 1
        self._resize_anchor_row = top_row if edge == 'bottom' else bottom_row
        self._resize_col = col

        self._span_top_row = top_row
        self._span_len = span

    def _compute_span(self, anchor_row: int, target_row: int, edge: str):
        """Calculează noul start și noua lungime de span în funcție de anchor și poziția target."""
        if edge == 'bottom':
            start_row = anchor_row
            end_row = max(target_row, start_row)
        else:
            end_row = anchor_row
            start_row = min(target_row, end_row)
        new_span = max(1, end_row - start_row + 1)
        return start_row, new_span

    def _ensure_item_at(self, start_row: int, col: int):
        """Se asigură că există un item la (start_row, col), mutându-l dacă este necesar."""
        item = self.item(start_row, col)
        if item is not None:
            return item
        anchor_item = self.item(self._resize_anchor_row, col)
        if anchor_item is not None:
            self.takeItem(self._resize_anchor_row, col)
            self.setItem(start_row, col, anchor_item)
            return anchor_item
        return None

    def _update_resize(self, target_row: int):
        """Actualizează vizual și în model redimensionarea unui eveniment în timpul drag-ului."""
        if target_row < 0:
            return

        start_row, new_span = self._compute_span(
            self._resize_anchor_row, target_row, self._resize_edge
        )
        if self._resize_edge == 'bottom':
            limit = self._nearest_blocking_event(
                self._span_top_row,
                start_row + new_span - 1,
                self._resize_col,
                'bottom'
            )
            if limit is not None:
                new_span = max(1, limit - self._span_top_row + 1)

        else:
            limit = self._nearest_blocking_event(
                start_row,
                self._span_top_row + self._span_len - 1,
                self._resize_col,
                'top'
            )
            if limit is not None:
                start_row = limit
                new_span = (self._span_top_row + self._span_len) - start_row

        start_row, new_span = self._constraint_within_day(start_row, new_span)

        if self._span_top_row is not None:
            old_top = self._span_top_row
            old_col = self._resize_col
            ev = self.events_by_pos.pop((old_top, old_col), None)

            self.setSpan(self._span_top_row, self._resize_col, 1, 1)

            moved = False
            if self._span_top_row is not None and self._span_len >= 1:
                old_start = self._span_top_row
                old_end = min(self._span_top_row + self._span_len - 1, self.rowCount() - 1)
                for r in range(old_start, old_end + 1):
                    it = self.item(r, self._resize_col)
                    if it is not None:
                        self.takeItem(r, self._resize_col)
                        self.setItem(start_row, self._resize_col, it)
                        moved = True
                        break

            if not moved:
                self._ensure_item_at(start_row, self._resize_col)

            self.setSpan(start_row, self._resize_col, new_span, 1)

            if ev is not None:
                ev.start_row = start_row
                ev.day_col = old_col
                ev.duration = new_span
                self.events_by_pos[(start_row, old_col)] = ev

        self._span_top_row = start_row
        self._span_len = new_span

    def _end_resize(self):
        """Finalizează operația de resize și resetează starea internă."""
        self._resize_active = False
        self._resize_edge = None
        self._resize_anchor_row = None
        self._resize_col = None
        self._span_top_row = None
        self._span_len = 1
        self.viewport().unsetCursor()

    def _update_edge_cursor(self, item: QTableWidgetItem, y: float):
        """Actualizează cursorul pentru a indica posibilitatea de resize la marginea unui eveniment."""
        near_top, near_bottom = self._is_near_vertical_edge(item, y)
        if near_top or near_bottom:
            self.viewport().setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.viewport().unsetCursor()

    # ===================== Overlap & ajustare evenimente =====================

    def _intervals_overlap(self, a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
        """Verifică dacă două intervale [a_start, a_end] și [b_start, b_end] se suprapun."""
        return not (a_end < b_start or a_start > b_end)

    def _overlap_info(self, start_row: int, span_len: int, col: int):
        """Returnează primul eveniment care se suprapune cu intervalul dat și informații despre overlap."""
        new_start = start_row
        new_end = start_row + max(1, span_len) - 1
        for (srow, scol), ev in self.events_by_pos.items():
            if scol != col:
                continue
            ev_start = ev.start_row
            ev_end = ev.start_row + ev.duration - 1
            if not (new_end < ev_start or new_start > ev_end):
                overlap_len = min(new_end, ev_end) - max(new_start, ev_start) + 1
                top_is_new = new_start < ev_start
                return ev, overlap_len, top_is_new
        return None, 0, False

    def _find_overlaps(self, start_row: int, span_len: int, col: int):
        """Returnează toate evenimentele care se suprapun cu intervalul dat pe o coloană, ordonate de sus în jos."""
        overlaps = []
        new_start = start_row
        new_end = start_row + max(1, span_len) - 1

        for (srow, scol), ev in self.events_by_pos.items():
            if scol != col:
                continue
            if self._dragging_src is not None and (srow, scol) == self._dragging_src:
                continue
            ev_start = ev.start_row
            ev_end = ev.start_row + ev.duration - 1
            if not (new_end < ev_start or new_start > ev_end):
                overlaps.append(ev)

        overlaps.sort(key=lambda e: e.start_row)
        return overlaps

    def _shrink_event_by(self, ev: CalendarEvent, cut: int):
        """Micșorează un eveniment din partea de jos cu 'cut' rânduri și actualizează UI + model."""
        if cut <= 0:
            return
        old_top = ev.start_row
        col = ev.day_col
        new_duration = max(1, ev.duration - cut)
        if new_duration == ev.duration:
            return

        self.setSpan(old_top, col, 1, 1)
        self.setSpan(old_top, col, new_duration, 1)

        ev.duration = new_duration
        self.events_by_pos[(old_top, col)] = ev

    def _shrink_event_from_top(self, ev: CalendarEvent, cut: int):
        """Micșorează un eveniment din partea de sus cu 'cut' rânduri și mută start_row-ul în jos."""
        if cut <= 0:
            return

        old_start = ev.start_row
        col = ev.day_col
        old_duration = ev.duration

        new_duration = max(0, old_duration - cut)
        if new_duration <= 0:
            self.setSpan(old_start, col, 1, 1)
            self.takeItem(old_start, col)
            self.events_by_pos.pop((old_start, col), None)
            return

        new_start = old_start + cut

        item = self.item(old_start, col)
        if item is None:
            return

        self.setSpan(old_start, col, 1, 1)
        self.takeItem(old_start, col)

        self.setItem(new_start, col, item)
        self.setSpan(new_start, col, new_duration, 1)

        self.events_by_pos.pop((old_start, col), None)
        ev.start_row = new_start
        ev.duration = new_duration
        self.events_by_pos[(new_start, col)] = ev

    def _split_event_middle(self, ev: CalendarEvent, new_start: int, new_end: int):
        """Împarte un eveniment în două părți, separând intervalul [new_start, new_end] din mijloc."""
        ev_start = ev.start_row
        ev_end = ev.start_row + ev.duration - 1
        col = ev.day_col

        if not (ev_start < new_start <= new_end < ev_end):
            return

        duration_top = new_start - ev_start
        duration_bottom = ev_end - new_end

        if duration_top < 0 or duration_bottom < 0:
            return

        orig_item = self.item(ev_start, col)
        if orig_item is None:
            return

        self.setSpan(ev_start, col, 1, 1)
        self.events_by_pos.pop((ev_start, col), None)

        if duration_top > 0:
            self.setItem(ev_start, col, orig_item)
            self.setSpan(ev_start, col, duration_top, 1)

            ev.start_row = ev_start
            ev.duration = duration_top
            self.events_by_pos[(ev_start, col)] = ev
        else:
            orig_item = None

        if duration_bottom > 0:
            bottom_start = new_end + 1

            item_bottom = QTableWidgetItem(ev.title)
            item_bottom.setTextAlignment(Qt.AlignCenter)
            item_bottom.setBackground(ev.color)
            self.setItem(bottom_start, col, item_bottom)
            self.setSpan(bottom_start, col, duration_bottom, 1)

            ev_bottom = CalendarEvent(
                title=ev.title,
                start_row=bottom_start,
                day_col=col,
                duration=duration_bottom,
                color=ev.color,
                description=ev.description
            )
            self.events_by_pos[(bottom_start, col)] = ev_bottom

    # ===================== Constrangeri ======================

    def _nearest_blocking_event(self, start_row: int, end_row: int, col: int, edge: str):
        """Găsește cel mai apropiat eveniment care blochează extinderea resize-ului în sus sau în jos."""
        for (srow, scol), ev in self.events_by_pos.items():
            if scol != col:
                continue

            ev_start = ev.start_row
            ev_end = ev.start_row + ev.duration - 1

            if (ev_start == start_row and ev_end == end_row):
                continue

            if edge == 'bottom':
                if ev_start > start_row and ev_start <= end_row:
                    return ev_start - 1
            else:
                if ev_end < end_row and ev_end >= start_row:
                    return ev_end + 1

        return None

    def _constraint_same_day_column(self, original_ev: CalendarEvent, drop_col: int) -> int:
        """
        Constrângere: un eveniment nu poate fi mutat pe altă zi.
        Întoarce mereu coloana din ziua originală a evenimentului, ignorând coloana target.
        """
        if original_ev is None:
            return drop_col
        return original_ev.day_col

    def _constraint_within_day(self, start_row: int, duration: int) -> Tuple[int, int]:
        """
        Constrângere: limitează start_row și durata astfel încât evenimentul să rămână în intervalul [0, rowCount-1].
        Ajustează start_row și duration dacă ar ieși în afara zilei.
        """
        if self.rowCount() <= 0:
            return 0, 0

        # clamp start_row în [0, rowCount-1]
        start_row = max(0, min(start_row, self.rowCount() - 1))

        # dacă start_row + duration depășește ultima oră, scurtăm durata
        max_duration = self.rowCount() - start_row
        duration = max(1, min(duration, max_duration))

        return start_row, duration

    def _constraint_inside_window(self, row: int, col: int) -> bool:
        """Constrângere: verifică dacă poziția (row, col) este în interiorul tabelului."""
        if row < 0 or col < 0:
            return False
        if row >= self.rowCount() or col >= self.columnCount():
            return False
        return True

    # ===================== HELPERS =====================

    def reset_table(self):
        """Resetează complet conținutul: șterge item-urile, span-urile și modelul de evenimente."""
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                if self.rowSpan(r, c) != 1 or self.columnSpan(r, c) != 1:
                    self.setSpan(r, c, 1, 1)
                item = self.item(r, c)
                if item is not None:
                    self.takeItem(r, c)

        self.events_by_pos.clear()
        self.viewport().update()

    def set_day_labels(self, labels: list[str]):
        """Setează label-urile pentru header-ul orizontal (zilele)."""
        if len(labels) == self.columnCount():
            self.setHorizontalHeaderLabels(labels)

    def set_disabled_columns(self, cols: list[int]):
        """Marchează anumite coloane (zile) ca fiind 'disabled' (nu se pot edita)."""
        self.disabled_cols = set(cols)

        # actualizăm vizual header-ul ca să se vadă că sunt gri
        from PySide6.QtGui import QBrush

        for c in range(self.columnCount()):
            item = self.horizontalHeaderItem(c)
            if item is None:
                continue
            if c in self.disabled_cols:
                item.setForeground(QBrush(QColor("#777777")))   # gri
            else:
                item.setForeground(QBrush(QColor("#f5f5f5")))   # alb normal

        self.viewport().update()
