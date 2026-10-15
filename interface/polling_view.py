"""
Vista per la selezione e verifica del Polling Rate USB (Frequenza di campionamento).
Supporta 125 Hz, 250 Hz, 500 Hz, 1000 Hz con applicazione immediata sul mouse Razer
e include un'area di benchmark interattiva per misurare in tempo reale i report al secondo.
"""

import time
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QButtonGroup, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QTimer


class MouseTestPad(QFrame):
    """Area interattiva per muovere il cursore e misurare il polling rate reale."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setStyleSheet("""
            MouseTestPad {
                background-color: #1a1a1a;
                border: 2px dashed #333333;
                border-radius: 8px;
            }
            MouseTestPad:hover {
                border: 2px dashed #00FF66;
                background-color: #162419;
            }
        """)
        self.setMinimumHeight(150)
        self.events_count = 0
        self.last_reset = time.perf_counter()
        self.current_hz = 0
        self.peak_hz = 0

    def mouseMoveEvent(self, event) -> None:
        self.events_count += 1
        super().mouseMoveEvent(event)

    def calculate_hz(self) -> int:
        now = time.perf_counter()
        delta = now - self.last_reset
        if delta >= 0.5:
            hz = int(self.events_count / delta)
            self.current_hz = hz
            if hz > self.peak_hz:
                self.peak_hz = hz
            self.events_count = 0
            self.last_reset = now
        return self.current_hz


class PollingView(QWidget):
    """
    Componente interfaccia per la configurazione del Polling Rate hardware.
    """

    polling_rate_changed = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_rate = 1000
        self._setup_ui()

        # Timer per il benchmark del test pad
        self._bench_timer = QTimer(self)
        self._bench_timer.timeout.connect(self._update_benchmark)
        self._bench_timer.start(100)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        header_card = QFrame()
        header_card.setProperty("class", "card")
        header_layout = QVBoxLayout(header_card)

        title = QLabel("Polling Rate USB / Wireless")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        sub = QLabel("Frequenza con cui il mouse invia la posizione del sensore al computer (rapporto di latenza)")
        sub.setStyleSheet("color: #888888; font-size: 12px;")
        header_layout.addWidget(title)
        header_layout.addWidget(sub)
        layout.addWidget(header_card)

        # Pulsanti di selezione 125, 250, 500, 1000 Hz
        select_card = QFrame()
        select_card.setProperty("class", "card")
        select_layout = QVBoxLayout(select_card)

        sec_title = QLabel("Seleziona Frequenza:")
        sec_title.setStyleSheet("font-weight: 600; font-size: 14px; margin-bottom: 8px;")
        select_layout.addWidget(sec_title)

        rates_layout = QHBoxLayout()
        rates_layout.setSpacing(12)

        self.rate_buttons = {}
        self.btn_group = QButtonGroup(self)

        rate_specs = [
            (1000, "1000 Hz", "Latenza: 1 ms\n(Ideale per Gaming competitivo)"),
            (500, "500 Hz", "Latenza: 2 ms\n(Ottimo compromesso batteria)"),
            (250, "250 Hz", "Latenza: 4 ms\n(Risparmio energetico)"),
            (125, "125 Hz", "Latenza: 8 ms\n(Ufficio standard / Max autonomia)")
        ]

        for hz, title_str, desc in rate_specs:
            btn = QPushButton(f"{title_str}\n\n{desc}")
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #222222;
                    color: #cccccc;
                    border: 2px solid #333333;
                    border-radius: 8px;
                    padding: 16px;
                    font-size: 13px;
                    text-align: center;
                }
                QPushButton:hover {
                    border: 2px solid #555555;
                    background-color: #282828;
                }
                QPushButton:checked {
                    border: 2px solid #00FF66;
                    background-color: #172a1d;
                    color: #00FF66;
                    font-weight: bold;
                }
            """)
            btn.setMinimumHeight(110)
            btn.clicked.connect(lambda _, h=hz: self._on_rate_clicked(h))
            self.rate_buttons[hz] = btn
            self.btn_group.addButton(btn)
            rates_layout.addWidget(btn)

        select_layout.addLayout(rates_layout)

        # Stato applicazione
        self.lbl_apply_status = QLabel("Frequenza attuale applicata: 1000 Hz (Hardware OK)")
        self.lbl_apply_status.setStyleSheet("color: #00FF66; font-size: 13px; font-weight: 600; margin-top: 10px;")
        select_layout.addWidget(self.lbl_apply_status)

        layout.addWidget(select_card)

        # Area Test Benchmark in tempo reale
        bench_card = QFrame()
        bench_card.setProperty("class", "card")
        bench_layout = QVBoxLayout(bench_card)

        bench_title = QLabel("Test Benchmark Polling Rate in Tempo Reale")
        bench_title.setStyleSheet("font-size: 14px; font-weight: 600;")
        bench_sub = QLabel("Muovi il cursore all'interno dell'area tratteggiata per verificare la frequenza reale ricevuta da Windows:")
        bench_sub.setStyleSheet("color: #888888; font-size: 12px; margin-bottom: 8px;")
        bench_layout.addWidget(bench_title)
        bench_layout.addWidget(bench_sub)

        self.test_pad = MouseTestPad()
        bench_layout.addWidget(self.test_pad)

        metrics_layout = QHBoxLayout()
        self.lbl_current_hz = QLabel("Frequenza Rilevata: <b>0 Hz</b>")
        self.lbl_current_hz.setStyleSheet("font-size: 15px; color: #00FF66;")

        self.lbl_peak_hz = QLabel("Picco Raggiunto: <b>0 Hz</b>")
        self.lbl_peak_hz.setStyleSheet("font-size: 15px; color: #a0a0a0;")

        btn_reset_peak = QPushButton("Azzera Picco")
        btn_reset_peak.setProperty("class", "btn-secondary")
        btn_reset_peak.clicked.connect(self._reset_peak)

        metrics_layout.addWidget(self.lbl_current_hz)
        metrics_layout.addWidget(self.lbl_peak_hz)
        metrics_layout.addStretch()
        metrics_layout.addWidget(btn_reset_peak)
        bench_layout.addLayout(metrics_layout)

        layout.addWidget(bench_card)
        layout.addStretch()

    def set_polling_rate(self, rate_hz: int) -> None:
        """Aggiorna il pulsante attivo."""
        self._current_rate = rate_hz
        if rate_hz in self.rate_buttons:
            self.rate_buttons[rate_hz].setChecked(True)
            self.lbl_apply_status.setText(f"Frequenza attuale applicata: {rate_hz} Hz (Hardware OK)")

    def _on_rate_clicked(self, rate_hz: int) -> None:
        self._current_rate = rate_hz
        self.lbl_apply_status.setText(f"Applicazione {rate_hz} Hz al dispositivo in corso...")
        self.polling_rate_changed.emit(rate_hz)

    def set_hardware_status(self, text: str, is_ok: bool = True) -> None:
        color = "#00FF66" if is_ok else "#ff6666"
        self.lbl_apply_status.setText(text)
        self.lbl_apply_status.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 600; margin-top: 10px;")

    def _update_benchmark(self) -> None:
        if self.isVisible():
            hz = self.test_pad.calculate_hz()
            self.lbl_current_hz.setText(f"Frequenza Rilevata: <b>{hz} Hz</b>")
            self.lbl_peak_hz.setText(f"Picco Raggiunto: <b>{self.test_pad.peak_hz} Hz</b>")

    def _reset_peak(self) -> None:
        self.test_pad.peak_hz = 0
        self.lbl_peak_hz.setText("Picco Raggiunto: <b>0 Hz</b>")
