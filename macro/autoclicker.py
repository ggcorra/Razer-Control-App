"""
Modulo Autoclicker ad alte prestazioni.
Supporta intervallo in millisecondi configurabile, randomizzazione del jitter per evitare pattern rigidi,
selezione del pulsante del mouse (sinistro, destro, centrale) e modalità continua o a tenuta.
"""

import time
import random
import threading
from typing import Callable, Optional
from hardware.windows_hook import send_mouse_click


class AutoClicker:
    """
    Motore di autoclick multi-thread controllabile tramite hotkey o interfaccia.
    """

    def __init__(
        self,
        interval_ms: int = 50,
        randomize: bool = False,
        jitter_ms: int = 10,
        button: str = "left",
        on_state_change: Optional[Callable[[bool], None]] = None
    ):
        self.interval_ms = interval_ms
        self.randomize = randomize
        self.jitter_ms = jitter_ms
        self.button = button
        self.on_state_change = on_state_change

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    def set_config(self, interval_ms: int, randomize: bool, jitter_ms: int, button: str) -> None:
        """Aggiorna i parametri dell'autoclicker al volo."""
        self.interval_ms = max(5, int(interval_ms))
        self.randomize = randomize
        self.jitter_ms = max(0, int(jitter_ms))
        self.button = button

    def start(self) -> bool:
        """Avvia il thread dell'autoclicker."""
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

        if self.on_state_change:
            self.on_state_change(True)
        return True

    def stop(self) -> bool:
        """Ferma il thread dell'autoclicker."""
        with self._lock:
            if not self._running:
                return False
            self._running = False

        if self.on_state_change:
            self.on_state_change(False)
        return True

    def toggle(self) -> bool:
        """Inverte lo stato attivo/disattivo."""
        if self._running:
            self.stop()
            return False
        else:
            self.start()
            return True

    def _run_loop(self) -> None:
        """Loop di click continuo ad alta precisione."""
        while self._running:
            send_mouse_click(self.button, action="click")

            # Calcolo del ritardo con eventuale jitter
            delay_sec = self.interval_ms / 1000.0
            if self.randomize and self.jitter_ms > 0:
                jitter = random.uniform(-self.jitter_ms, self.jitter_ms) / 1000.0
                delay_sec = max(0.002, delay_sec + jitter)

            # Precision sleep
            end_time = time.perf_counter() + delay_sec
            while time.perf_counter() < end_time and self._running:
                time.sleep(0.001)
