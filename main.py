"""
Punto di ingresso principale per Razer Viper V3 HyperSpeed Controller.
Inizializza le impostazioni, gestisce l'hardware, avvia l'interfaccia grafica PySide6
e abilita il ridimensionamento High-DPI per schermi moderni di Windows 11.
"""

import sys
import os
import ctypes
import traceback

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor

# Assicura che la directory root del progetto sia nel PYTHONPATH
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.settings_manager import SettingsManager
from hardware.mouse_device import RazerMouseDevice
from interface.main_window import MainWindow


def create_app_icon() -> QIcon:
    """Genera programmaticamente un'icona con il logo verde Razer per l'app e la tray bar."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Cerchio di sfondo scuro
    painter.setBrush(QColor("#181818"))
    painter.setPen(QColor("#00FF66"))
    painter.drawEllipse(4, 4, 56, 56)

    # Disegna sagoma mouse stilizzata
    painter.setBrush(QColor("#00FF66"))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(22, 16, 20, 32, 10, 10)

    # Rotellina
    painter.setBrush(QColor("#181818"))
    painter.drawRoundedRect(30, 22, 4, 10, 2, 2)

    painter.end()
    return QIcon(pixmap)


def main():
    # Abilita High-DPI scaling nativo per Windows 11
    if sys.platform == "win32":
        try:
            # Imposta ID applicazione esplicito per la barra delle applicazioni di Windows
            myappid = "razer.viper.v3.controller.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("Razer Viper V3 Controller")
    app.setOrganizationName("RazerController")
    app.setWindowIcon(create_app_icon())

    # Caricamento configurazione persistente
    if getattr(sys, "frozen", False):
        appdata_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RazerViperController")
        os.makedirs(appdata_dir, exist_ok=True)
        config_path = os.path.join(appdata_dir, "settings.json")
    else:
        config_path = os.path.join(BASE_DIR, "settings.json")

    settings = SettingsManager(config_path)

    # Inizializzazione hardware per Razer Viper V3 HyperSpeed
    device = RazerMouseDevice()

    # Creazione finestra principale
    window = MainWindow(settings, device)
    window.setWindowIcon(create_app_icon())
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
