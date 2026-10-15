"""
Vista per il monitoraggio della batteria e stato hardware del Razer Viper V3 HyperSpeed.
Visualizza percentuale, stato di carica/scarica, notifica soglia critica (<20%)
e dettagli diagnostici del protocollo hardware USB/HID.
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal


class BatteryView(QWidget):
    """
    Componente interfaccia per stato batteria e diagnostica hardware.
    """

    refresh_requested = Signal()
    threshold_changed = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        header_card = QFrame()
        header_card.setProperty("class", "card")
        header_layout = QVBoxLayout(header_card)

        title = QLabel("Stato Batteria & Connessione Wireless")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        sub = QLabel("Monitoraggio in tempo reale del livello di carica del Razer Viper V3 HyperSpeed")
        sub.setStyleSheet("color: #888888; font-size: 12px;")
        header_layout.addWidget(title)
        header_layout.addWidget(sub)
        layout.addWidget(header_card)

        # Card Principale Batteria
        main_card = QFrame()
        main_card.setProperty("class", "card")
        main_layout = QVBoxLayout(main_card)
        main_layout.setSpacing(16)

        # Barra di avanzamento e percentuale grande
        top_row = QHBoxLayout()
        self.lbl_percentage = QLabel("-- %")
        self.lbl_percentage.setStyleSheet("font-size: 54px; font-weight: bold; color: #00FF66;")
        top_row.addWidget(self.lbl_percentage)

        self.lbl_charging_badge = QLabel("A Batteria (Wireless)")
        self.lbl_charging_badge.setStyleSheet("""
            background-color: #222222; color: #ffffff;
            padding: 8px 16px; border-radius: 6px; font-weight: 600; font-size: 14px;
        """)
        top_row.addWidget(self.lbl_charging_badge, alignment=Qt.AlignVCenter)
        top_row.addStretch()

        btn_refresh = QPushButton("🔄 Aggiorna Ora")
        btn_refresh.setProperty("class", "btn-secondary")
        btn_refresh.clicked.connect(self.refresh_requested.emit)
        top_row.addWidget(btn_refresh, alignment=Qt.AlignVCenter)

        main_layout.addLayout(top_row)

        # Barra di progresso
        self.bar_battery = QProgressBar()
        self.bar_battery.setRange(0, 100)
        self.bar_battery.setValue(0)
        self.bar_battery.setTextVisible(False)
        self.bar_battery.setFixedHeight(12)
        self.bar_battery.setStyleSheet("""
            QProgressBar {
                background-color: #252525;
                border-radius: 6px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #00FF66;
                border-radius: 6px;
            }
        """)
        main_layout.addWidget(self.bar_battery)

        layout.addWidget(main_card)

        # Card Configurazione Notifiche
        notif_card = QFrame()
        notif_card.setProperty("class", "card")
        notif_layout = QHBoxLayout(notif_card)

        self.chk_notif = QCheckBox("Invia notifica di sistema Windows se la carica scende sotto il:")
        self.chk_notif.setChecked(True)
        notif_layout.addWidget(self.chk_notif)

        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(5, 50)
        self.spin_threshold.setValue(20)
        self.spin_threshold.setSuffix(" %")
        self.spin_threshold.valueChanged.connect(self.threshold_changed.emit)
        notif_layout.addWidget(self.spin_threshold)
        notif_layout.addStretch()

        layout.addWidget(notif_card)

        # Card Dettagli Tecnici Protocollo
        diag_card = QFrame()
        diag_card.setProperty("class", "card")
        diag_layout = QVBoxLayout(diag_card)
        diag_layout.setSpacing(10)

        diag_title = QLabel("Dettagli Tecnici Protocollo Hardware Razer")
        diag_title.setStyleSheet("font-size: 14px; font-weight: 600;")
        diag_layout.addWidget(diag_title)

        self.lbl_diag_model = QLabel("• Modello Rilevato: Razer Viper V3 HyperSpeed")
        self.lbl_diag_vidpid = QLabel("• Hardware IDs: VID 0x1532, PID 0x00B8")
        self.lbl_diag_report = QLabel("• Protocollo Feature Report: 90 Byte Razer (OpenRazer compliant)")
        self.lbl_diag_raw = QLabel("• Valore Hardware Raw: In attesa di lettura...")

        for lbl in (self.lbl_diag_model, self.lbl_diag_vidpid, self.lbl_diag_report, self.lbl_diag_raw):
            lbl.setStyleSheet("color: #a0a0a0; font-size: 12px;")
            diag_layout.addWidget(lbl)

        layout.addWidget(diag_card)
        layout.addStretch()

    def update_battery(self, percentage: int, is_charging: bool, raw_val: int = 0) -> None:
        """Aggiorna la visualizzazione dello stato energetico."""
        percentage = max(0, min(100, int(percentage)))
        self.lbl_percentage.setText(f"{percentage}%")
        self.bar_battery.setValue(percentage)

        # Colore in base alla carica
        if percentage <= 20:
            color = "#ff4444"
            badge_bg = "#4a1818"
        elif percentage <= 50:
            color = "#ffaa00"
            badge_bg = "#3d2b10"
        else:
            color = "#00FF66"
            badge_bg = "#172a1d"

        self.lbl_percentage.setStyleSheet(f"font-size: 54px; font-weight: bold; color: {color};")
        self.bar_battery.setStyleSheet(f"""
            QProgressBar {{
                background-color: #252525;
                border-radius: 6px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)

        if is_charging:
            self.lbl_charging_badge.setText("⚡ In Ricarica (USB)")
            self.lbl_charging_badge.setStyleSheet("""
                background-color: #00441b; color: #00FF66;
                padding: 8px 16px; border-radius: 6px; font-weight: 600; font-size: 14px;
            """)
        else:
            self.lbl_charging_badge.setText("A Batteria (Wireless 2.4 GHz)")
            self.lbl_charging_badge.setStyleSheet(f"""
                background-color: {badge_bg}; color: #ffffff;
                padding: 8px 16px; border-radius: 6px; font-weight: 600; font-size: 14px;
            """)

        self.lbl_diag_raw.setText(f"• Valore Hardware Raw: {raw_val} / 255 (Conversione {percentage}%)")
