"""
Vista per la rimappatura dei tasti fisici del Razer Viper V3 HyperSpeed.
Permette di riassegnare ciascun tasto fisico a click alternativi, scorciatoie da tastiera,
ripetizione continua (Rapid-Fire mentre tenuto premuto), ciclo DPI o macro salvate.
"""

from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDialog, QComboBox, QLineEdit, QSpinBox, QFormLayout,
    QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Signal


BUTTON_NAMES = {
    "button_left": "Pulsante Sinistro (Click 1)",
    "button_right": "Pulsante Destro (Click 2)",
    "button_middle": "Click Rotellina (Pulsante Centrale)",
    "button_x1": "Tasto Laterale 1 (Indietro / Back)",
    "button_x2": "Tasto Laterale 2 (Avanti / Forward)",
    "button_dpi": "Tasto DPI Fisico"
}


class ButtonEditDialog(QDialog):
    """Dialogo modale per configurare l'azione assegnata a un tasto."""

    def __init__(self, button_id: str, current_config: Dict[str, Any], available_macros: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configura {BUTTON_NAMES.get(button_id, button_id)}")
        self.setMinimumWidth(380)

        self.button_id = button_id
        self.available_macros = available_macros
        self.result_config = dict(current_config)

        self._setup_ui(current_config)

    def _setup_ui(self, cfg: Dict[str, Any]) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form = QFormLayout()

        # Tipo azione
        self.combo_type = QComboBox()
        self.combo_type.addItems([
            "Predefinito Windows",
            "Click Mouse Alternativo",
            "Scorciatoia Tastiera",
            "Rapid-Fire (Ripetizione mentre premuto)",
            "Esegui Macro",
            "Ciclo Profilo DPI"
        ])

        # Seleziona tipo corrente
        t = cfg.get("type", "default")
        type_idx_map = {
            "default": 0,
            "mouse_remap": 1,
            "key_combo": 2,
            "rapid_fire": 3,
            "macro": 4,
            "dpi_cycle": 5
        }
        self.combo_type.setCurrentIndex(type_idx_map.get(t, 0))
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Tipo Azione:", self.combo_type)

        # 1. Click alternativo
        self.combo_mouse_btn = QComboBox()
        self.combo_mouse_btn.addItems(["Sinistro", "Destro", "Centrale", "Laterale 1 (Back)", "Laterale 2 (Forward)"])
        mouse_target = cfg.get("target_button", "left")
        mouse_map = {"left": 0, "right": 1, "middle": 2, "x1": 3, "x2": 4}
        self.combo_mouse_btn.setCurrentIndex(mouse_map.get(mouse_target, 0))
        form.addRow("Pulsante Destinazione:", self.combo_mouse_btn)

        # 2. Scorciatoia da tastiera
        self.txt_keys = QLineEdit()
        self.txt_keys.setPlaceholderText("es: ctrl+c oppure alt+tab oppure enter")
        if t == "key_combo":
            self.txt_keys.setText("+".join(cfg.get("keys", ["ctrl", "c"])))
        form.addRow("Scorciatoia:", self.txt_keys)

        # 3. Rapid Fire intervallo
        self.spin_rapid_interval = QSpinBox()
        self.spin_rapid_interval.setRange(10, 1000)
        self.spin_rapid_interval.setSingleStep(10)
        self.spin_rapid_interval.setValue(cfg.get("interval_ms", 40))
        self.spin_rapid_interval.setSuffix(" ms")
        form.addRow("Intervallo Rapid Fire:", self.spin_rapid_interval)

        # 4. Scelta Macro
        self.combo_macro = QComboBox()
        self.combo_macro.addItems(self.available_macros if self.available_macros else ["Nessuna Macro Registrata"])
        if t == "macro" and cfg.get("macro_name") in self.available_macros:
            self.combo_macro.setCurrentText(cfg.get("macro_name"))
        form.addRow("Macro da eseguire:", self.combo_macro)

        layout.addLayout(form)

        # Pulsanti OK / Annulla
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._on_type_changed(self.combo_type.currentIndex())

    def _on_type_changed(self, idx: int) -> None:
        self.combo_mouse_btn.setVisible(idx in (1, 3))
        self.txt_keys.setVisible(idx == 2)
        self.spin_rapid_interval.setVisible(idx == 3)
        self.combo_macro.setVisible(idx == 4)

    def _on_accept(self) -> None:
        idx = self.combo_type.currentIndex()
        if idx == 0:  # default
            self.result_config = {"type": "default"}
        elif idx == 1:  # mouse remap
            m_map = {0: "left", 1: "right", 2: "middle", 3: "x1", 4: "x2"}
            target = m_map.get(self.combo_mouse_btn.currentIndex(), "left")
            self.result_config = {"type": "mouse_remap", "target_button": target}
        elif idx == 2:  # key combo
            keys_raw = self.txt_keys.text().strip()
            if not keys_raw:
                QMessageBox.warning(self, "Attenzione", "Inserisci almeno un tasto o combinazione.")
                return
            keys = [k.strip().lower() for k in keys_raw.split("+") if k.strip()]
            self.result_config = {"type": "key_combo", "keys": keys, "label": keys_raw}
        elif idx == 3:  # rapid fire
            m_map = {0: "left", 1: "right", 2: "middle", 3: "x1", 4: "x2"}
            target = m_map.get(self.combo_mouse_btn.currentIndex(), "left")
            self.result_config = {
                "type": "rapid_fire",
                "target_button": target,
                "interval_ms": self.spin_rapid_interval.value()
            }
        elif idx == 4:  # macro
            macro_sel = self.combo_macro.currentText()
            self.result_config = {"type": "macro", "macro_name": macro_sel}
        elif idx == 5:  # dpi cycle
            self.result_config = {"type": "dpi_cycle", "action": "cycle"}

        self.accept()


class RemapView(QWidget):
    """
    Componente interfaccia per la configurazione della rimappatura di tutti i tasti.
    """

    remapping_updated = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_mappings: Dict[str, Any] = {}
        self.available_macros: List[str] = []
        self._btn_label_widgets: Dict[str, QLabel] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_card = QFrame()
        header_card.setProperty("class", "card")
        header_layout = QVBoxLayout(header_card)

        title = QLabel("Rimappatura Tasti & Azioni Mouse")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        sub = QLabel("Riassegna qualsiasi tasto del Razer Viper V3 a combinazioni, macro o ripetizione rapida (Rapid-Fire).")
        sub.setStyleSheet("color: #888888; font-size: 12px;")
        header_layout.addWidget(title)
        header_layout.addWidget(sub)
        layout.addWidget(header_card)

        # Griglia tasti
        buttons_card = QFrame()
        buttons_card.setProperty("class", "card")
        buttons_layout = QVBoxLayout(buttons_card)
        buttons_layout.setSpacing(10)

        for btn_id, btn_name in BUTTON_NAMES.items():
            row = QHBoxLayout()
            row.setSpacing(12)

            name_lbl = QLabel(f"<b>{btn_name}</b>")
            name_lbl.setMinimumWidth(260)

            act_lbl = QLabel("Predefinito")
            act_lbl.setStyleSheet("color: #00FF66; font-weight: 500;")
            self._btn_label_widgets[btn_id] = act_lbl

            btn_edit = QPushButton("Modifica")
            btn_edit.setProperty("class", "btn-secondary")
            btn_edit.setFixedWidth(85)
            btn_edit.clicked.connect(lambda _, b=btn_id: self._on_edit_button(b))

            btn_reset = QPushButton("Reset")
            btn_reset.setProperty("class", "btn-secondary")
            btn_reset.setFixedWidth(65)
            btn_reset.clicked.connect(lambda _, b=btn_id: self._on_reset_button(b))

            row.addWidget(name_lbl)
            row.addWidget(act_lbl, 1)
            row.addWidget(btn_edit)
            row.addWidget(btn_reset)
            buttons_layout.addLayout(row)

            # Divisore sottile tranne ultimo
            if btn_id != list(BUTTON_NAMES.keys())[-1]:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setStyleSheet("background-color: #262626;")
                buttons_layout.addWidget(sep)

        layout.addWidget(buttons_card)

        # Info soppressione eventi
        info_card = QFrame()
        info_card.setProperty("class", "card")
        info_l = QHBoxLayout(info_card)
        lbl_info = QLabel("ℹ️ L'intercettazione dei tasti utilizza un Hook Win32 a bassa latenza che sopprime l'azione nativa originale se rimappata.")
        lbl_info.setStyleSheet("color: #888888; font-size: 12px;")
        info_l.addWidget(lbl_info)
        layout.addWidget(info_card)

        layout.addStretch()

    def set_mappings(self, mappings: Dict[str, Any], macros: List[str]) -> None:
        """Carica le impostazioni attuali e aggiorna la UI."""
        self.current_mappings = dict(mappings)
        self.available_macros = list(macros)

        for btn_id in BUTTON_NAMES.keys():
            cfg = self.current_mappings.get(btn_id, {"type": "default"})
            lbl = self._btn_label_widgets.get(btn_id)
            if lbl:
                lbl.setText(self._format_config_text(cfg))

    def _format_config_text(self, cfg: Dict[str, Any]) -> str:
        t = cfg.get("type", "default")
        if t == "default":
            return "Predefinito di sistema"
        elif t == "mouse_remap":
            return f"Click {cfg.get('target_button', 'left').capitalize()}"
        elif t == "key_combo":
            return f"Tasti: {cfg.get('label', '+'.join(cfg.get('keys', [])))}"
        elif t == "rapid_fire":
            return f"Rapid-Fire ({cfg.get('target_button', 'left')}, {cfg.get('interval_ms', 40)}ms)"
        elif t == "macro":
            return f"Macro: '{cfg.get('macro_name', '')}'"
        elif t == "dpi_cycle":
            return "Cambia Profilo DPI (Ciclo)"
        return "Non configurato"

    def _on_edit_button(self, btn_id: str) -> None:
        current_cfg = self.current_mappings.get(btn_id, {"type": "default"})
        dlg = ButtonEditDialog(btn_id, current_cfg, self.available_macros, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.current_mappings[btn_id] = dlg.result_config
            lbl = self._btn_label_widgets.get(btn_id)
            if lbl:
                lbl.setText(self._format_config_text(dlg.result_config))
            self.remapping_updated.emit(self.current_mappings)

    def _on_reset_button(self, btn_id: str) -> None:
        self.current_mappings[btn_id] = {"type": "default"}
        lbl = self._btn_label_widgets.get(btn_id)
        if lbl:
            lbl.setText("Predefinito di sistema")
        self.remapping_updated.emit(self.current_mappings)
