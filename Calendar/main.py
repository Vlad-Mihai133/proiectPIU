import sys
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QTableWidget, QTableWidgetItem, QInputDialog
)
from PySide6.QtCore import Qt, QMimeData, QPoint
from PySide6.QtGui import QDrag, QMouseEvent, QColor


# === Nou: model simplu pentru evenimente ===
@dataclass
class CalendarEvent:
    title: str
    start_row: int
    day_col: int
    duration: int  # în ore (număr de rânduri)
    color: QColor


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
        # pt resize
        self.setMouseTracking(True)
        self._resize_active = False
        self._resize_edge = None  # 'top' sau 'bottom'
        self._resize_anchor_row = None
        self._resize_col = None
        self._resize_margin_px = 6
        self._span_top_row = None
        self._span_len = 1
        self._last_drop_target = None

        # === Nou: stocare evenimente și sursa curentă a drag-ului ===
        # Cheie: (row, col) al rândului de START (top) al evenimentului
        self.events_by_pos: dict[tuple[int, int], CalendarEvent] = {}
        self._dragging_src: tuple[int, int] | None = None

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
            posf = event.position()  # QPointF
            p = posf.toPoint()  # QPoint pentru itemAt/rowAt/columnAt
            item = self.itemAt(p)
            if item is not None:
                y = posf.y()
                near_top, near_bottom = self._is_near_vertical_edge(item, y)
                if near_top or near_bottom:
                    self._begin_resize(item, 'top' if near_top else 'bottom')
                    return  # stop: suntem in mod resize
            # altfel: drag normal
            self.dragStartPosition = p  # stocăm QPoint
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resize_active:
            self._update_resize(self.rowAt(event.position().toPoint().y()))
            return

        # feedback vizual cursor pe margini
        posf = event.position()
        p = posf.toPoint()
        item = self.itemAt(p)
        if item is not None:
            self._update_edge_cursor(item, posf.y())
        else:
            self.viewport().unsetCursor()

        # fluxul de drag (păstrat ca în logică originală)
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
        span_len = max(1, self.rowSpan(src_row, src_col))

        # === Nou: memorează sursa pentru a muta modelul la drop ===
        self._dragging_src = (src_row, src_col)

        drag = QDrag(self)
        mimeData = QMimeData()
        mimeData.setText(f"{span_len}|{item.text()}")  # NEMODIFICAT: aceeași încărcătură MIME
        mimeData.setColorData(item.background().color())
        drag.setMimeData(mimeData)

        result = drag.exec(Qt.MoveAction)
        if result == Qt.MoveAction:
            if self._last_drop_target != (src_row, src_col):
                self.setSpan(src_row, src_col, 1, 1)
                self.takeItem(src_row, src_col)
            self._last_drop_target = None
            self._dragging_src = None

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._resize_active:
            self._end_resize()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Adauga un eveniment prin dublu click.
        import random
        posf = event.position()  # QPointF
        p = posf.toPoint()  # QPoint

        item = self.itemAt(p)
        row = self.rowAt(p.y())
        col = self.columnAt(p.x())
        if row < 0 or col < 0:
            return

        if item is None:
            text, ok = QInputDialog.getText(self, "Add Event", "Event name:")
            if ok and text.strip():
                new_item = QTableWidgetItem(text.strip())
                new_item.setTextAlignment(Qt.AlignCenter)
                random_color = QColor(random.randint(100, 255),
                                      random.randint(100, 255),
                                      random.randint(100, 255))
                new_item.setBackground(random_color)
                self.setItem(row, col, new_item)
                # === Nou: salvează în model ===
                self.events_by_pos[(row, col)] = CalendarEvent(
                    title=text.strip(), start_row=row, day_col=col, duration=1, color=random_color
                )

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        """Mută evenimentul; dacă suprapune peste altul, cel de sus va fi micșorat."""
        pos = event.position().toPoint()
        row = self.rowAt(pos.y())
        col = self.columnAt(pos.x())
        if row < 0 or col < 0:
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

        # cap la limite
        if row + span_len > self.rowCount():
            row = max(0, self.rowCount() - span_len)

        # --- Nou: detectează overlap și micșorează DOAR intersecția ---
        overlapped, overlap_len, top_is_new = self._overlap_info(row, span_len, col)
        if overlapped is not None and overlap_len > 0:
            if top_is_new:
                # Evenimentul DROP-uit e 'de sus' => micșorează-l pe acesta cu exact overlap_len
                span_len = max(1, span_len - overlap_len)
                # Reajustează dacă depășește finalul după micșorare (de obicei nu e cazul)
                if row + span_len > self.rowCount():
                    row = max(0, self.rowCount() - span_len)
            else:
                # Evenimentul EXISTENT e 'de sus' => micșorează-l pe acesta cu exact overlap_len
                self._shrink_event_by(overlapped, overlap_len)

        self._last_drop_target = (row, col)

        if text:
            # eliberează celula țintă (span 1x1) înainte de a plasa
            self.setSpan(row, col, 1, 1)

            new_item = QTableWidgetItem(text)
            new_item.setTextAlignment(Qt.AlignCenter)
            new_item.setBackground(color if color else Qt.yellow)
            self.setItem(row, col, new_item)

            # setează span-ul final
            self.setSpan(row, col, span_len, 1)

            # === sincronizează modelul CalendarEvent ===
            if self._dragging_src is not None:
                srow, scol = self._dragging_src
                ev = self.events_by_pos.pop((srow, scol), None)
            else:
                ev = None

            if ev is None:
                ev = CalendarEvent(
                    title=text, start_row=row, day_col=col, duration=span_len,
                    color=color if color else QColor(Qt.yellow)
                )
            else:
                ev.title = text
                ev.start_row = row
                ev.day_col = col
                ev.duration = span_len
                if color:
                    ev.color = color

            self.events_by_pos[(row, col)] = ev

        event.acceptProposedAction()

    def _is_near_vertical_edge(self, item, y):
        rect = self.visualItemRect(item)
        return (
            abs(y - rect.top()) <= self._resize_margin_px,
            abs(y - rect.bottom()) <= self._resize_margin_px
        )

    def _begin_resize(self, item, edge):
        self._resize_active = True
        self._resize_edge = edge
        row = self.row(item)
        col = self.column(item)
        span = max(1, self.rowSpan(row, col))
        top_row = row
        bottom_row = row + span - 1
        self._resize_anchor_row = top_row if edge == 'bottom' else bottom_row
        self._resize_col = col

        self._span_top_row = top_row
        self._span_len = span

    def _compute_span(self, anchor_row, target_row, edge):
        if edge == 'bottom':
            start_row = anchor_row
            end_row = max(target_row, start_row)
        else:
            end_row = anchor_row
            start_row = min(target_row, end_row)
        new_span = max(1, end_row - start_row + 1)
        return start_row, new_span

    def _ensure_item_at(self, start_row, col):
        item = self.item(start_row, col)
        if item is not None:
            return item
        anchor_item = self.item(self._resize_anchor_row, col)
        if anchor_item is not None:
            self.takeItem(self._resize_anchor_row, col)
            self.setItem(start_row, col, anchor_item)
            return anchor_item
        return None

    def _update_resize(self, target_row):
        if target_row < 0:
            return

        start_row, new_span = self._compute_span(
            self._resize_anchor_row, target_row, self._resize_edge
        )

        if self._span_top_row is not None:
            # înainte să schimbăm vizual, actualizăm și modelul (dacă avem eveniment în (old_top, col))
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

            # sincronizează modelul cu noua poziție
            if ev is not None:
                ev.start_row = start_row
                ev.day_col = old_col
                ev.duration = new_span
                self.events_by_pos[(start_row, old_col)] = ev

        self._span_top_row = start_row
        self._span_len = new_span

    def _end_resize(self):
        self._resize_active = False
        self._resize_edge = None
        self._resize_anchor_row = None
        self._resize_col = None
        self._span_top_row = None
        self._span_len = 1
        self.viewport().unsetCursor()

    def _update_edge_cursor(self, item, y):
        near_top, near_bottom = self._is_near_vertical_edge(item, y)
        if near_top or near_bottom:
            self.viewport().setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.viewport().unsetCursor()

    # --- Nou: info completă despre overlap ---
    def _overlap_info(self, start_row: int, span_len: int, col: int):
        """
        Returnează (ev, overlap_len, top_is_new) sau (None, 0, False) dacă nu e overlap.
        top_is_new = True dacă evenimentul NOU (drop) e 'de sus' (are start_row mai mic).
        """
        new_start = start_row
        new_end = start_row + max(1, span_len) - 1
        for (srow, scol), ev in self.events_by_pos.items():
            if scol != col:
                continue
            ev_start = ev.start_row
            ev_end = ev.start_row + ev.duration - 1
            if not (new_end < ev_start or new_start > ev_end):
                overlap_len = min(new_end, ev_end) - max(new_start, ev_start) + 1
                # 'de sus' = cel cu start_row mai mic; dacă egal, considerăm EXISTENTUL de sus
                top_is_new = new_start < ev_start
                return ev, overlap_len, top_is_new
        return None, 0, False

    # --- Nou: micșorează un eveniment exact cu 'cut' rânduri din partea de jos ---
    def _shrink_event_by(self, ev: CalendarEvent, cut: int):
        """
        Reduce durata evenimentului 'ev' cu 'cut' rânduri (min 1), tăind din partea de jos.
        Sincronizează UI + model.
        """
        if cut <= 0:
            return
        old_top = ev.start_row
        col = ev.day_col
        new_duration = max(1, ev.duration - cut)
        if new_duration == ev.duration:
            return

        # Resetează span-ul și aplică noul span
        self.setSpan(old_top, col, 1, 1)
        self.setSpan(old_top, col, new_duration, 1)

        # Actualizează modelul
        ev.duration = new_duration
        self.events_by_pos[(old_top, col)] = ev


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
