from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QTextEdit, QDialogButtonBox, QLabel, QMessageBox


class EventEditDialog(QDialog):
    """Dialog pentru editarea / crearea unui eveniment (nume + descriere)."""

    def __init__(self, title: str = "", description: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Event")

        self.title_edit = QLineEdit(title)
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(description)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Title:"))
        layout.addWidget(self.title_edit)
        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.desc_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self
        )

        buttons.button(QDialogButtonBox.Ok).clicked.connect(self._validate_title)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _validate_title(self):
        """Nu permite OK dacă titlul este gol."""
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Invalid Title", "Title cannot be empty.")
            return
        self.accept()

    def get_values(self):
        """Returnează titlul și descrierea introduse în dialog."""
        return self.title_edit.text().strip(), self.desc_edit.toPlainText().strip()

