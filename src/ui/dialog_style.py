"""Estilo común (tema oscuro Radical Records) para los diálogos secundarios."""

BG, BG2, BG3, BORDER = "#0a0b0e", "#121419", "#1a1c22", "#232733"
TEXT, TEXT2 = "#eceef2", "#8c93a4"
ACCENT, ACCENT2, GREEN, RED, WARN = "#ff1e38", "#ff3e55", "#22c55e", "#ef4444", "#f59e0b"

DIALOG_QSS = f"""
    QDialog {{ background: {BG}; }}
    QLabel {{ background: transparent; color: {TEXT}; }}
    QPushButton {{
        background: {BG3}; color: {TEXT}; border: 1px solid {BORDER};
        border-radius: 8px; padding: 8px 14px; font-size: 12px;
    }}
    QPushButton:hover {{ border-color: {ACCENT}; }}
    QPushButton:disabled {{ color: {TEXT2}; border-color: {BG3}; }}
    QPushButton#primary {{ background: {ACCENT}; color: #fff; border: none; font-weight: 700; }}
    QPushButton#primary:hover {{ background: {ACCENT2}; }}
    QPushButton#danger {{ color: {RED}; }}
    QPushButton#danger:hover {{ border-color: {RED}; }}
    QComboBox, QLineEdit, QSpinBox {{
        background: {BG3}; color: {TEXT}; border: 1px solid {BORDER};
        border-radius: 6px; padding: 5px 8px; font-size: 12px;
    }}
    QComboBox QAbstractItemView {{
        background: {BG2}; color: {TEXT}; selection-background-color: {ACCENT};
        border: 1px solid {BORDER};
    }}
    QCheckBox {{ color: {TEXT}; font-size: 12px; spacing: 6px; background: transparent; }}
    QCheckBox::indicator {{
        width: 14px; height: 14px; border: 1px solid {BORDER}; border-radius: 3px; background: {BG3};
    }}
    QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
    QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 8px; top: -1px; }}
    QTabBar::tab {{
        background: {BG2}; color: {TEXT2}; padding: 8px 16px; border: 1px solid {BORDER};
        border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px;
    }}
    QTabBar::tab:selected {{ background: {BG3}; color: {TEXT}; }}
    QTableWidget, QListWidget {{
        background: {BG2}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 8px;
        gridline-color: {BORDER}; font-size: 12px; outline: none;
    }}
    QTableWidget::item:selected, QListWidget::item:selected {{ background: {ACCENT}33; color: {TEXT}; }}
    QHeaderView::section {{
        background: {BG3}; color: {TEXT2}; border: none; border-bottom: 1px solid {BORDER};
        padding: 6px; font-size: 11px; font-weight: 700;
    }}
"""
