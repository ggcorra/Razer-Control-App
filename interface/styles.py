"""
Fogli di stile moderni QSS per l'interfaccia grafica (Tema Scuro e Chiaro).
Ispirati all'estetica premium Razer (Nero profondo, accenti verde fluo #00FF66).
"""

DARK_THEME = """
QMainWindow {
    background-color: #121212;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
}

QWidget {
    background-color: transparent;
    color: #e0e0e0;
    font-size: 13px;
}

/* Sidebar di navigazione */
#sidebar {
    background-color: #181818;
    border-right: 1px solid #282828;
    min-width: 220px;
    max-width: 220px;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #a0a0a0;
    text-align: left;
    padding: 12px 20px;
    border: none;
    border-left: 3px solid transparent;
    font-size: 14px;
    font-weight: 500;
}

#sidebar QPushButton:hover {
    background-color: #222222;
    color: #ffffff;
}

#sidebar QPushButton:checked {
    background-color: #1f2a22;
    color: #00FF66;
    border-left: 3px solid #00FF66;
    font-weight: 600;
}

/* Card e Contenitori */
QFrame.card {
    background-color: #1e1e1e;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 16px;
}

QFrame.card:hover {
    border: 1px solid #383838;
}

/* Pulsanti principali */
QPushButton.btn-primary {
    background-color: #00FF66;
    color: #000000;
    font-weight: 600;
    border-radius: 6px;
    padding: 8px 18px;
    border: none;
}

QPushButton.btn-primary:hover {
    background-color: #26ff7d;
}

QPushButton.btn-primary:pressed {
    background-color: #00cc52;
}

QPushButton.btn-secondary {
    background-color: #282828;
    color: #ffffff;
    font-weight: 500;
    border-radius: 6px;
    padding: 8px 16px;
    border: 1px solid #383838;
}

QPushButton.btn-secondary:hover {
    background-color: #333333;
    border: 1px solid #484848;
}

QPushButton.btn-danger {
    background-color: #381818;
    color: #ff6666;
    font-weight: 500;
    border-radius: 6px;
    padding: 8px 16px;
    border: 1px solid #552222;
}

QPushButton.btn-danger:hover {
    background-color: #4a2020;
    color: #ff8888;
}

/* Slider DPI */
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #2b2b2b;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #00FF66;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #00FF66;
    width: 18px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #00FF66;
}

/* Input e Spinbox */
QSpinBox, QComboBox, QLineEdit {
    background-color: #252525;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
    font-weight: 500;
}

QSpinBox:focus, QComboBox:focus, QLineEdit:focus {
    border: 1px solid #00FF66;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

/* Tabelle */
QTableWidget {
    background-color: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    gridline-color: #222222;
    color: #e0e0e0;
}

QHeaderView::section {
    background-color: #222222;
    color: #a0a0a0;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #333333;
    font-weight: 600;
}

QTableWidget::item:selected {
    background-color: #1f3325;
    color: #00FF66;
}

/* Barra di stato */
QStatusBar {
    background-color: #141414;
    border-top: 1px solid #242424;
    color: #888888;
    font-size: 12px;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #444444;
    background-color: #252525;
}

QCheckBox::indicator:checked {
    background-color: #00FF66;
    border: 1px solid #00FF66;
}
"""

LIGHT_THEME = """
QMainWindow {
    background-color: #f4f6f8;
    color: #212529;
    font-family: 'Segoe UI', Arial, sans-serif;
}

QWidget {
    background-color: transparent;
    color: #212529;
    font-size: 13px;
}

#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e2e8f0;
    min-width: 220px;
    max-width: 220px;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #4a5568;
    text-align: left;
    padding: 12px 20px;
    border: none;
    border-left: 3px solid transparent;
    font-size: 14px;
    font-weight: 500;
}

#sidebar QPushButton:hover {
    background-color: #edf2f7;
    color: #1a202c;
}

#sidebar QPushButton:checked {
    background-color: #e6f9ed;
    color: #009933;
    border-left: 3px solid #009933;
    font-weight: 600;
}

QFrame.card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px;
}

QPushButton.btn-primary {
    background-color: #00aa44;
    color: #ffffff;
    font-weight: 600;
    border-radius: 6px;
    padding: 8px 18px;
    border: none;
}

QPushButton.btn-primary:hover {
    background-color: #008837;
}

QPushButton.btn-secondary {
    background-color: #edf2f7;
    color: #2d3748;
    font-weight: 500;
    border-radius: 6px;
    padding: 8px 16px;
    border: 1px solid #cbd5e0;
}

QPushButton.btn-secondary:hover {
    background-color: #e2e8f0;
}

QPushButton.btn-danger {
    background-color: #fed7d7;
    color: #c53030;
    font-weight: 500;
    border-radius: 6px;
    padding: 8px 16px;
    border: 1px solid #feb2b2;
}

QPushButton.btn-danger:hover {
    background-color: #feb2b2;
}

QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #cbd5e0;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #00aa44;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #00aa44;
    width: 18px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 9px;
}

QSpinBox, QComboBox, QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e0;
    border-radius: 6px;
    padding: 6px 10px;
    color: #2d3748;
    font-weight: 500;
}

QSpinBox:focus, QComboBox:focus, QLineEdit:focus {
    border: 1px solid #00aa44;
}

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    gridline-color: #edf2f7;
    color: #2d3748;
}

QHeaderView::section {
    background-color: #f7fafc;
    color: #718096;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    font-weight: 600;
}

QTableWidget::item:selected {
    background-color: #e6f9ed;
    color: #00aa44;
}

QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e2e8f0;
    color: #718096;
    font-size: 12px;
}
"""
