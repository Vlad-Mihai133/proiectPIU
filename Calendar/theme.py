APP_DARK_STYLE = """
        QMainWindow {
            background-color: #222831;
            color: #f5f5f5;
        }
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
        QLabel#WeekLabel {
            color: #f5f5f5;
            font-size: 13px;
        }
        QWidget#CentralWidget {
            background-color: #222831;
        }

        /* TOOLBAR SUS */
        QToolBar {
            background-color: #111720;
            border-bottom: 1px solid #393e46;
        }
        QToolBar QToolButton {
            background: transparent;
            color: #f5f5f5;
            padding: 4px 8px;
            border-radius: 4px;
        }
        QToolBar QToolButton:hover {
            background-color: #393e46;
        }
        QTableCornerButton::section {
            background-color: #393e46;      /* la fel ca zilele */
            border: 1px solid #4b4f57;      /* la fel ca QHeaderView::section */
        }
        /* BUTOANE (Prev week / Next week / Save / Load etc.) */
        QPushButton {
            background-color: #00adb5;
            color: #ffffff;
            border-radius: 6px;
            padding: 6px 14px;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #01c3cd;
        }
        QPushButton:disabled {
            background-color: #444;
        }

        /* TABELUL DE ORAR (ScheduleTable) */
        QTableWidget {
            background-color: #222831;
            alternate-background-color: #1f252d;
            color: #f5f5f5;
            gridline-color: #393e46;
            selection-background-color: #00adb5;
            selection-color: #ffffff;
        }

        QHeaderView::section {
            background-color: #393e46;
            color: #f5f5f5;
            padding: 4px;
            border: 1px solid #4b4f57;
            font-size: 12px;
        }

        /* Scrollbars dark (optional) */
        QScrollBar:vertical {
            background: #222831;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #393e46;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: #4b4f57;
        }

        QScrollBar:horizontal {
            background: #222831;
            height: 10px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: #393e46;
            min-width: 20px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #4b4f57;
        }
        """
