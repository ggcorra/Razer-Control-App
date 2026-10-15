"""
Vista completa per Macro e Automazioni:
1. Autoclicker ad alta precisione con jitter randomizzato e attivazione globale.
2. Registratore di macro per click, coordinate cursore e tastiera con ritardi reali.
3. Editor interattivo della sequenza registrata (modifica ritardi, eliminazione step).
4. Riproduttore con loop configurabile (ripetizioni fisse o infinito) e hotkey globali.
"""

from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSpinBox, QCheckBox, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QInputDialog, QMessageBox,
    QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QTimer


class MacroView(QWidget):
    """
    Componente interfaccia per Autoclicker e gestione/registrazione/editing macro.
    """

    autoclicker_config_changed = Signal(dict)
    autoclicker_toggled = Signal(bool)

    macro_record_started = Signal(bool)   # record_moves
    macro_record_stopped = Signal()
    macro_play_started = Signal(str, int) # (macro_name, loop_count)
    macro_play_stopped = Signal()
    macro_saved = Signal(str, dict)       # (macro_name, data)
    macro_deleted = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.macros_data: Dict[str, Any] = {}
        self.current_steps: List[Dict[str, Any]] = []
        self.is_recording = False
        self.is_playing = False
        self._block_signals = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # -------------------------------------------------------------
        # SEZIONE 1: AUTOCLICKER
        # -------------------------------------------------------------
        ac_card = QFrame()
        ac_card.setProperty("class", "card")
        ac_layout = QVBoxLayout(ac_card)
        ac_layout.setSpacing(12)

        ac_header = QHBoxLayout()
        ac_title = QLabel("⚡ Autoclicker ad Alta Velocità")
        ac_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        ac_header.addWidget(ac_title)
        ac_header.addStretch()

        self.lbl_ac_status = QLabel("INATTIVO")
        self.lbl_ac_status.setStyleSheet("""
            background-color: #2b2b2b; color: #888888;
            padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;
        """)
        ac_header.addWidget(self.lbl_ac_status)
        ac_layout.addLayout(ac_header)

        # Parametri Autoclicker
        ac_controls = QHBoxLayout()
        ac_controls.setSpacing(16)

        # Intervallo
        box_int = QVBoxLayout()
        box_int.addWidget(QLabel("Intervallo (ms):"))
        self.spin_ac_interval = QSpinBox()
        self.spin_ac_interval.setRange(5, 5000)
        self.spin_ac_interval.setValue(50)
        self.spin_ac_interval.setSuffix(" ms")
        self.spin_ac_interval.valueChanged.connect(self._emit_autoclicker_config)
        box_int.addWidget(self.spin_ac_interval)
        ac_controls.addLayout(box_int)

        # Randomizzazione Jitter
        box_jit = QVBoxLayout()
        self.chk_ac_random = QCheckBox("Randomizza intervallo (+/-):")
        self.chk_ac_random.setChecked(True)
        self.chk_ac_random.toggled.connect(self._emit_autoclicker_config)
        box_jit.addWidget(self.chk_ac_random)

        self.spin_ac_jitter = QSpinBox()
        self.spin_ac_jitter.setRange(0, 1000)
        self.spin_ac_jitter.setValue(10)
        self.spin_ac_jitter.setSuffix(" ms")
        self.spin_ac_jitter.valueChanged.connect(self._emit_autoclicker_config)
        box_jit.addWidget(self.spin_ac_jitter)
        ac_controls.addLayout(box_jit)

        # Pulsante Mouse
        box_btn = QVBoxLayout()
        box_btn.addWidget(QLabel("Pulsante:"))
        self.combo_ac_button = QComboBox()
        self.combo_ac_button.addItems(["Sinistro (Left)", "Destro (Right)", "Centrale (Middle)"])
        self.combo_ac_button.currentIndexChanged.connect(self._emit_autoclicker_config)
        box_btn.addWidget(self.combo_ac_button)
        ac_controls.addLayout(box_btn)

        # Tasto Start / Stop
        self.btn_toggle_ac = QPushButton("Avvia Autoclicker (F6)")
        self.btn_toggle_ac.setProperty("class", "btn-primary")
        self.btn_toggle_ac.setMinimumHeight(42)
        self.btn_toggle_ac.clicked.connect(self._toggle_autoclicker_btn)
        ac_controls.addWidget(self.btn_toggle_ac, alignment=Qt.AlignBottom)

        ac_layout.addLayout(ac_controls)
        layout.addWidget(ac_card)

        # -------------------------------------------------------------
        # SEZIONE 2: REGISTRATORE ED EDITOR MACRO
        # -------------------------------------------------------------
        rec_card = QFrame()
        rec_card.setProperty("class", "card")
        rec_layout = QVBoxLayout(rec_card)
        rec_layout.setSpacing(12)

        # Header Macro
        rec_header = QHBoxLayout()
        rec_title = QLabel("🎬 Registratore & Editor Macro")
        rec_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        rec_header.addWidget(rec_title)
        rec_header.addStretch()

        rec_header.addWidget(QLabel("Libreria Macro:"))
        self.combo_macro_list = QComboBox()
        self.combo_macro_list.setMinimumWidth(160)
        self.combo_macro_list.currentTextChanged.connect(self._on_selected_macro_changed)
        rec_header.addWidget(self.combo_macro_list)

        self.btn_save_macro = QPushButton("Salva con Nome")
        self.btn_save_macro.setProperty("class", "btn-secondary")
        self.btn_save_macro.clicked.connect(self._on_save_macro_clicked)
        rec_header.addWidget(self.btn_save_macro)

        self.btn_del_macro = QPushButton("Elimina")
        self.btn_del_macro.setProperty("class", "btn-danger")
        self.btn_del_macro.clicked.connect(self._on_delete_macro_clicked)
        rec_header.addWidget(self.btn_del_macro)

        rec_layout.addLayout(rec_header)

        # Barra comandi registrazione
        bar_layout = QHBoxLayout()
        self.chk_record_moves = QCheckBox("Cattura movimenti cursore")
        self.chk_record_moves.setChecked(False)
        bar_layout.addWidget(self.chk_record_moves)

        self.btn_record = QPushButton("● Registra Macro (F9)")
        self.btn_record.setProperty("class", "btn-danger")
        self.btn_record.clicked.connect(self._on_record_btn_clicked)
        bar_layout.addWidget(self.btn_record)

        bar_layout.addStretch()

        # Configurazione Loop
        bar_layout.addWidget(QLabel("Ripeti:"))
        self.spin_loops = QSpinBox()
        self.spin_loops.setRange(1, 1000)
        self.spin_loops.setValue(1)
        self.spin_loops.setSuffix(" volte")
        bar_layout.addWidget(self.spin_loops)

        self.chk_infinite_loop = QCheckBox("Loop Infinito")
        self.chk_infinite_loop.toggled.connect(lambda chk: self.spin_loops.setEnabled(not chk))
        bar_layout.addWidget(self.chk_infinite_loop)

        self.btn_play = QPushButton("▶ Riproduci Macro (F10)")
        self.btn_play.setProperty("class", "btn-primary")
        self.btn_play.clicked.connect(self._on_play_btn_clicked)
        bar_layout.addWidget(self.btn_play)

        rec_layout.addLayout(bar_layout)

        # Tabella Editor Eventi
        self.table_steps = QTableWidget(0, 4)
        self.table_steps.setHorizontalHeaderLabels(["Azione", "Dettaglio", "Ritardo (sec)", "Rimuovi"])
        self.table_steps.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_steps.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_steps.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_steps.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_steps.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_steps.cellChanged.connect(self._on_table_cell_changed)
        rec_layout.addWidget(self.table_steps)

        # Pulsanti sotto la tabella
        tbl_footer = QHBoxLayout()
        lbl_hint = QLabel("💡 Fai doppio click sul valore 'Ritardo' per modificarlo a mano.")
        lbl_hint.setStyleSheet("color: #888888; font-size: 11px;")
        tbl_footer.addWidget(lbl_hint)
        tbl_footer.addStretch()

        btn_clear_table = QPushButton("Svuota Sequenza")
        btn_clear_table.setProperty("class", "btn-secondary")
        btn_clear_table.clicked.connect(self._clear_steps)
        tbl_footer.addWidget(btn_clear_table)
        rec_layout.addLayout(tbl_footer)

        layout.addWidget(rec_card)

    # -------------------------------------------------------------
    # GESTIONE AUTOCLICKER
    # -------------------------------------------------------------
    def set_autoclicker_active(self, active: bool) -> None:
        """Aggiorna lo stato visivo dell'autoclicker."""
        if active:
            self.lbl_ac_status.setText("ATTIVO")
            self.lbl_ac_status.setStyleSheet("""
                background-color: #172a1d; color: #00FF66;
                padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;
            """)
            self.btn_toggle_ac.setText("Arresta Autoclicker (F6)")
            self.btn_toggle_ac.setProperty("class", "btn-danger")
            self.btn_toggle_ac.setStyleSheet("background-color: #4a2020; color: #ff8888;")
        else:
            self.lbl_ac_status.setText("INATTIVO")
            self.lbl_ac_status.setStyleSheet("""
                background-color: #2b2b2b; color: #888888;
                padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;
            """)
            self.btn_toggle_ac.setText("Avvia Autoclicker (F6)")
            self.btn_toggle_ac.setProperty("class", "btn-primary")
            self.btn_toggle_ac.setStyleSheet("")

    def _toggle_autoclicker_btn(self) -> None:
        current_text = self.lbl_ac_status.text()
        new_state = (current_text != "ATTIVO")
        self.autoclicker_toggled.emit(new_state)

    def _emit_autoclicker_config(self) -> None:
        btn_map = {0: "left", 1: "right", 2: "middle"}
        cfg = {
            "interval_ms": self.spin_ac_interval.value(),
            "randomize": self.chk_ac_random.isChecked(),
            "random_jitter_ms": self.spin_ac_jitter.value(),
            "button": btn_map.get(self.combo_ac_button.currentIndex(), "left")
        }
        self.autoclicker_config_changed.emit(cfg)

    # -------------------------------------------------------------
    # GESTIONE MACRO
    # -------------------------------------------------------------
    def set_macros_library(self, macros: Dict[str, Any], select_name: Optional[str] = None) -> None:
        """Popola l'elenco delle macro salvate."""
        self._block_signals = True
        self.macros_data = dict(macros)
        self.combo_macro_list.clear()
        self.combo_macro_list.addItems(list(self.macros_data.keys()))
        if select_name and select_name in self.macros_data:
            self.combo_macro_list.setCurrentText(select_name)
        elif self.combo_macro_list.count() > 0:
            self._load_macro_to_table(self.combo_macro_list.currentText())
        self._block_signals = False

    def set_recording_state(self, is_rec: bool) -> None:
        self.is_recording = is_rec
        if is_rec:
            self.btn_record.setText("⏹ Ferma Registrazione (F9)")
            self.btn_record.setStyleSheet("background-color: #cc0000; color: #ffffff; font-weight: bold;")
        else:
            self.btn_record.setText("● Registra Macro (F9)")
            self.btn_record.setStyleSheet("")

    def set_playing_state(self, is_play: bool) -> None:
        self.is_playing = is_play
        if is_play:
            self.btn_play.setText("⏹ Ferma Riproduzione (F10)")
            self.btn_play.setStyleSheet("background-color: #ffaa00; color: #000000; font-weight: bold;")
        else:
            self.btn_play.setText("▶ Riproduci Macro (F10)")
            self.btn_play.setStyleSheet("")

    def append_recorded_step(self, step: Dict[str, Any]) -> None:
        """Aggiunge in tempo reale un evento registrato alla tabella."""
        self.current_steps.append(step)
        self._add_step_row(step, len(self.current_steps) - 1)

    def set_steps(self, steps: List[Dict[str, Any]]) -> None:
        """Sostituisce l'intera sequenza di step."""
        self.current_steps = list(steps)
        self._refresh_table()

    def _refresh_table(self) -> None:
        self._block_signals = True
        self.table_steps.setRowCount(0)
        for i, step in enumerate(self.current_steps):
            self._add_step_row(step, i)
        self._block_signals = False

    def _add_step_row(self, step: Dict[str, Any], row_idx: int) -> None:
        self._block_signals = True
        self.table_steps.insertRow(row_idx)

        stype = step.get("type", "")
        detail = ""
        if "mouse" in stype:
            detail = f"Tasto: {step.get('button', '')} ({step.get('x', '')}, {step.get('y', '')})"
        elif "key" in stype:
            detail = f"Tasto: {step.get('key', '').upper()}"
        elif stype == "mouse_wheel":
            detail = f"Scroll: {step.get('delta', '')}"

        item_type = QTableWidgetItem(stype)
        item_type.setFlags(item_type.flags() & ~Qt.ItemIsEditable)

        item_detail = QTableWidgetItem(detail)
        item_detail.setFlags(item_detail.flags() & ~Qt.ItemIsEditable)

        item_delay = QTableWidgetItem(str(step.get("delay", 0.05)))

        btn_del = QPushButton("✕")
        btn_del.setFixedWidth(30)
        btn_del.setProperty("class", "btn-secondary")
        btn_del.clicked.connect(lambda _, r=row_idx: self._remove_step_row(r))

        self.table_steps.setItem(row_idx, 0, item_type)
        self.table_steps.setItem(row_idx, 1, item_detail)
        self.table_steps.setItem(row_idx, 2, item_delay)
        self.table_steps.setCellWidget(row_idx, 3, btn_del)

        self._block_signals = False

    def _remove_step_row(self, row: int) -> None:
        if 0 <= row < len(self.current_steps):
            self.current_steps.pop(row)
            self._refresh_table()

    def _clear_steps(self) -> None:
        self.current_steps = []
        self._refresh_table()

    def _on_table_cell_changed(self, row: int, col: int) -> None:
        if self._block_signals or col != 2:
            return
        item = self.table_steps.item(row, col)
        if item and 0 <= row < len(self.current_steps):
            try:
                new_delay = float(item.text().strip())
                self.current_steps[row]["delay"] = max(0.001, new_delay)
            except ValueError:
                item.setText(str(self.current_steps[row].get("delay", 0.05)))

    def _on_record_btn_clicked(self) -> None:
        if not self.is_recording:
            self._clear_steps()
            self.set_recording_state(True)
            self.macro_record_started.emit(self.chk_record_moves.isChecked())
        else:
            self.set_recording_state(False)
            self.macro_record_stopped.emit()

    def _on_play_btn_clicked(self) -> None:
        if not self.is_playing:
            if not self.current_steps:
                QMessageBox.warning(self, "Attenzione", "Nessuna sequenza di azioni da riprodurre.")
                return
            loops = -1 if self.chk_infinite_loop.isChecked() else self.spin_loops.value()
            self.set_playing_state(True)
            macro_name = self.combo_macro_list.currentText() or "Sequenza Corrente"
            self.macro_play_started.emit(macro_name, loops)
        else:
            self.set_playing_state(False)
            self.macro_play_stopped.emit()

    def _on_selected_macro_changed(self, name: str) -> None:
        if self._block_signals or not name:
            return
        self._load_macro_to_table(name)

    def _load_macro_to_table(self, name: str) -> None:
        if name in self.macros_data:
            data = self.macros_data[name]
            actions = data.get("actions", [])
            loops = data.get("loop_count", 1)
            self.spin_loops.setValue(max(1, loops))
            self.chk_infinite_loop.setChecked(loops <= 0)
            self.set_steps(actions)

    def _on_save_macro_clicked(self) -> None:
        if not self.current_steps:
            QMessageBox.warning(self, "Attenzione", "Registra o inserisci almeno un'azione prima di salvare.")
            return

        name, ok = QInputDialog.getText(self, "Salva Macro", "Nome identificativo per la macro:")
        if ok and name.strip():
            macro_obj = {
                "name": name.strip(),
                "loop_count": -1 if self.chk_infinite_loop.isChecked() else self.spin_loops.value(),
                "actions": list(self.current_steps)
            }
            self.macro_saved.emit(name.strip(), macro_obj)

    def _on_delete_macro_clicked(self) -> None:
        name = self.combo_macro_list.currentText()
        if not name:
            return
        reply = QMessageBox.question(
            self, "Elimina Macro",
            f"Sei sicuro di voler rimuovere la macro '{name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.macro_deleted.emit(name)
