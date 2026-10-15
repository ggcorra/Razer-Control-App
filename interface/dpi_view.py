"""
Vista per la gestione e configurazione DPI e profili del mouse.
Permette regolazione tramite slider, campo numerico, selezione rapida degli stadi,
gestione dei profili salvabili ("Gaming", "Lavoro", ecc.) e assegnazione hotkey per il cambio profilo.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox,
    QPushButton, QComboBox, QFrame, QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from typing import Optional, List


class DpiView(QWidget):
    """
    Componente interfaccia per il controllo DPI e gestione profili multipli.
    """

    dpi_changed = Signal(int)             # Emesso quando il DPI viene modificato dall'utente
    profile_switched = Signal(str)        # Emesso quando viene selezionato un profilo diverso
    profile_created = Signal(str, str)    # (nome_nuovo, nome_base)
    profile_deleted = Signal(str)         # (nome_profilo)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._block_signals = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # ---------------------------------------------------------
        # Intestazione e Gestione Profili
        # ---------------------------------------------------------
        header_card = QFrame()
        header_card.setProperty("class", "card")
        header_layout = QHBoxLayout(header_card)

        title_box = QVBoxLayout()
        title_label = QLabel("Configurazione Sensore & Profili DPI")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        sub_label = QLabel("Regola la sensibilità ottica del sensore Focus Pro 30K del Viper V3")
        sub_label.setStyleSheet("color: #888888; font-size: 12px;")
        title_box.addWidget(title_label)
        title_box.addWidget(sub_label)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Selettore profili
        prof_box = QHBoxLayout()
        prof_label = QLabel("Profilo Attivo:")
        prof_label.setStyleSheet("font-weight: 600;")
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(140)
        self.profile_combo.currentTextChanged.connect(self._on_profile_combo_changed)

        self.btn_new_profile = QPushButton("+ Nuovo")
        self.btn_new_profile.setProperty("class", "btn-secondary")
        self.btn_new_profile.clicked.connect(self._on_add_profile_clicked)

        self.btn_del_profile = QPushButton("Elimina")
        self.btn_del_profile.setProperty("class", "btn-danger")
        self.btn_del_profile.clicked.connect(self._on_delete_profile_clicked)

        prof_box.addWidget(prof_label)
        prof_box.addWidget(self.profile_combo)
        prof_box.addWidget(self.btn_new_profile)
        prof_box.addWidget(self.btn_del_profile)
        header_layout.addLayout(prof_box)

        main_layout.addWidget(header_card)

        # ---------------------------------------------------------
        # Card Principale DPI Slider & Valore
        # ---------------------------------------------------------
        dpi_card = QFrame()
        dpi_card.setProperty("class", "card")
        dpi_card_layout = QVBoxLayout(dpi_card)
        dpi_card_layout.setSpacing(16)

        # Valore attuale grande
        display_layout = QHBoxLayout()
        self.lbl_dpi_value = QLabel("1600")
        self.lbl_dpi_value.setStyleSheet("font-size: 48px; font-weight: bold; color: #00FF66;")

        unit_label = QLabel("DPI")
        unit_label.setStyleSheet("font-size: 20px; color: #888888; font-weight: bold; margin-bottom: 8px;")
        display_layout.addWidget(self.lbl_dpi_value, alignment=Qt.AlignBottom)
        display_layout.addWidget(unit_label, alignment=Qt.AlignBottom)
        display_layout.addStretch()

        # Spinbox numerico
        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(100, 30000)
        self.spin_dpi.setSingleStep(50)
        self.spin_dpi.setValue(1600)
        self.spin_dpi.setMinimumWidth(100)
        self.spin_dpi.valueChanged.connect(self._on_spin_changed)
        display_layout.addWidget(QLabel("Valore Esatto:"))
        display_layout.addWidget(self.spin_dpi)

        dpi_card_layout.addLayout(display_layout)

        # Slider orizzontale
        self.slider_dpi = QSlider(Qt.Horizontal)
        self.slider_dpi.setRange(100, 10000)
        self.slider_dpi.setSingleStep(50)
        self.slider_dpi.setPageStep(400)
        self.slider_dpi.setValue(1600)
        self.slider_dpi.valueChanged.connect(self._on_slider_changed)
        self.slider_dpi.sliderReleased.connect(self._on_slider_released)
        dpi_card_layout.addWidget(self.slider_dpi)

        # Preset rapidi (Stadi DPI)
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Stadi Rapidi:")
        preset_label.setStyleSheet("color: #888888;")
        preset_layout.addWidget(preset_label)

        for preset_val in [400, 800, 1200, 1600, 3200, 6400]:
            btn = QPushButton(str(preset_val))
            btn.setProperty("class", "btn-secondary")
            btn.setFixedWidth(65)
            btn.clicked.connect(lambda _, v=preset_val: self.set_dpi_value(v, emit_signal=True))
            preset_layout.addWidget(btn)

        preset_layout.addStretch()
        dpi_card_layout.addLayout(preset_layout)

        main_layout.addWidget(dpi_card)

        # ---------------------------------------------------------
        # Tasto Rapido e Stato Hardware
        # ---------------------------------------------------------
        info_card = QFrame()
        info_card.setProperty("class", "card")
        info_layout = QHBoxLayout(info_card)

        hotkey_info = QLabel("⚡ Tasto rapido globale cambio profilo: <b>F7</b> (funziona anche in game / in background)")
        hotkey_info.setStyleSheet("color: #a0a0a0; font-size: 13px;")
        info_layout.addWidget(hotkey_info)

        info_layout.addStretch()

        self.lbl_hw_status = QLabel("Protocollo: In sincronizzazione")
        self.lbl_hw_status.setStyleSheet("color: #00FF66; font-size: 12px; font-weight: bold;")
        info_layout.addWidget(self.lbl_hw_status)

        main_layout.addWidget(info_card)
        main_layout.addStretch()

    def set_profiles_list(self, profile_names: List[str], active_name: str) -> None:
        """Popola il selettore profili."""
        self._block_signals = True
        self.profile_combo.clear()
        self.profile_combo.addItems(profile_names)
        if active_name in profile_names:
            self.profile_combo.setCurrentText(active_name)
        self._block_signals = False

    def set_dpi_value(self, value: int, emit_signal: bool = False) -> None:
        """Aggiorna la visualizzazione del DPI corrente."""
        self._block_signals = True
        value = max(100, min(30000, int(value)))
        self.lbl_dpi_value.setText(str(value))
        self.spin_dpi.setValue(value)
        if value <= self.slider_dpi.maximum():
            self.slider_dpi.setValue(value)
        self._block_signals = False

        if emit_signal:
            self.dpi_changed.emit(value)

    def set_hardware_status(self, text: str, is_ok: bool = True) -> None:
        """Aggiorna l'etichetta di stato hardware."""
        color = "#00FF66" if is_ok else "#ff6666"
        self.lbl_hw_status.setText(text)
        self.lbl_hw_status.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")

    def _on_slider_changed(self, value: int) -> None:
        if self._block_signals:
            return
        self.lbl_dpi_value.setText(str(value))
        self.spin_dpi.blockSignals(True)
        self.spin_dpi.setValue(value)
        self.spin_dpi.blockSignals(False)

    def _on_slider_released(self) -> None:
        if self._block_signals:
            return
        val = self.slider_dpi.value()
        self.dpi_changed.emit(val)

    def _on_spin_changed(self, value: int) -> None:
        if self._block_signals:
            return
        self.lbl_dpi_value.setText(str(value))
        self.slider_dpi.blockSignals(True)
        if value <= self.slider_dpi.maximum():
            self.slider_dpi.setValue(value)
        self.slider_dpi.blockSignals(False)
        self.dpi_changed.emit(value)

    def _on_profile_combo_changed(self, text: str) -> None:
        if self._block_signals or not text:
            return
        self.profile_switched.emit(text)

    def _on_add_profile_clicked(self) -> None:
        name, ok = QInputDialog.getText(self, "Nuovo Profilo", "Nome del nuovo profilo (es. FPS, MOBA):")
        if ok and name.strip():
            current_active = self.profile_combo.currentText()
            self.profile_created.emit(name.strip(), current_active)

    def _on_delete_profile_clicked(self) -> None:
        if self.profile_combo.count() <= 1:
            QMessageBox.warning(self, "Attenzione", "Impossibile eliminare l'unico profilo rimasto.")
            return

        current = self.profile_combo.currentText()
        reply = QMessageBox.question(
            self, "Conferma Eliminazione",
            f"Sei sicuro di voler eliminare il profilo '{current}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.profile_deleted.emit(current)
