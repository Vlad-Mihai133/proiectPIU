from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QLabel, QCheckBox, QMessageBox, QFrame,
    QSpinBox
)
from PySide6.QtCore import Qt


class EventEditDialog(QDialog):
    """Dialog pentru editarea / crearea unui eveniment (titlu, descriere, locked, info timp)."""

    def __init__(
        self,
        title: str = "",
        description: str = "",
        locked: bool = False,
        time_info: str | None = None,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Event details")
        self.setMinimumWidth(420)

        # Stilizare generală (poți ajusta culorile după gust)
        self.setStyleSheet("""
            QDialog {
                background-color: #222831;
                color: #f5f5f5;
            }
            QDialog QWidget {
                background-color: #393e46;
                color: #f5f5f5;
            }
            QLabel {
                font-size: 13px;
            }
            QLabel#TimeLabel {
                font-weight: bold;
                color: #00adb5;
                font-size: 14px;
            }
            QLabel#SectionTitle {
                font-weight: bold;
                margin-top: 8px;
                font-size: 13px;
            }
            QLineEdit, QTextEdit {
                background-color: #393e46;
                border: 1px solid #4b4f57;
                border-radius: 6px;
                padding: 6px;
                font-size: 13px;
                color: #f5f5f5;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #00adb5;
            }
            QCheckBox {
                font-size: 12px;
                margin-top: 6px;
            }
            QDialogButtonBox QPushButton {
                background-color: #00adb5;
                color: #ffffff;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 13px;
            }
            QDialogButtonBox QPushButton:hover {
                background-color: #01c3cd;
            }
            QDialogButtonBox QPushButton:disabled {
                background-color: #444;
            }
            QFrame {
                background-color: #393e46;
                color: #393e46;
            }
            QFrame[frameShape="4"] {  /* 4 = HLine */
                background-color: #393e46;
                max-height: 1px;
            }
            
        """)

        self.title_edit = QLineEdit(title)
        self.title_edit.setPlaceholderText("Event title…")

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(description)
        self.desc_edit.setPlaceholderText("Description, notes, attendees…")

        self.lock_check = QCheckBox("Locked (cannot be moved or overlapped)")
        self.lock_check.setChecked(locked)

        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 100)
        self.repeat_spin.setValue(1)
        self.repeat_spin.setToolTip("Number of weekly repetitions (0 = no repeat)")

        self.repeat_forever_check = QCheckBox("Repeat forever")
        self.repeat_forever_check.toggled.connect(
            lambda checked: self.repeat_spin.setEnabled(not checked)
        )


        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(QLabel("Repeat:"))
        repeat_layout.addWidget(self.repeat_spin)
        repeat_layout.addWidget(self.repeat_forever_check)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(8)
        main_layout.addWidget(self.lock_check)
        main_layout.addLayout(repeat_layout)

        # ===== Header cu info de timp =====
        if time_info:
            header_layout = QHBoxLayout()
            header_layout.setSpacing(6)

            time_label = QLabel(time_info)
            time_label.setObjectName("TimeLabel")

            header_layout.addWidget(time_label)
            header_layout.addStretch()

            main_layout.addLayout(header_layout)

        # Linie separator
        line_top = QFrame()
        line_top.setFrameShape(QFrame.HLine)
        line_top.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line_top)

        # ===== Titlu =====
        title_label = QLabel("Title")
        title_label.setObjectName("SectionTitle")
        main_layout.addWidget(title_label)
        main_layout.addWidget(self.title_edit)

        # ===== Descriere =====
        desc_label = QLabel("Description")
        desc_label.setObjectName("SectionTitle")
        main_layout.addWidget(desc_label)
        main_layout.addWidget(self.desc_edit, stretch=1)

        # Locked
        main_layout.addWidget(self.lock_check)

        # Linie separator jos
        line_bottom = QFrame()
        line_bottom.setFrameShape(QFrame.HLine)
        line_bottom.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line_bottom)

        # ===== Butoane =====
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self
        )
        # Validare manuală pe OK (nu lăsăm titlu gol)
        ok_button = buttons.button(QDialogButtonBox.Ok)
        if ok_button is not None:
            ok_button.clicked.connect(self._validate_title)
        else:
            # fallback în caz că butonul nu e creat încă
            buttons.accepted.connect(self._validate_title)

        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons, alignment=Qt.AlignRight)

        self.setLayout(main_layout)

    def _validate_title(self):
        """Nu permite OK dacă titlul este gol."""
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Invalid title", "Title cannot be empty.")
            return
        self.accept()

    def get_values(self):
        """Returnează titlul, descrierea și starea locked."""
        return (
            self.title_edit.text().strip(),
            self.desc_edit.toPlainText().strip(),
            self.lock_check.isChecked(),
            self.repeat_spin.value(),
            self.repeat_forever_check.isChecked(),
        )
