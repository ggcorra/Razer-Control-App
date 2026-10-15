"""
Modulo di riproduzione macro ad alta fedeltà temporale.
Supporta esecuzione singola, a numero prefissato di cicli o in loop infinito.
Utilizza SendInput Win32 per una latenza minima e massima precisione.
"""

import time
import threading
from typing import List, Dict, Any, Callable, Optional
from hardware.windows_hook import send_mouse_click, send_mouse_wheel, send_key_stroke
import ctypes


class MacroPlayer:
    """
    Esecutore di macro con controllo loop, interruzione immediata e callback di progresso.
    """

    def __init__(self, on_finish: Optional[Callable[[], None]] = None):
        self.on_finish = on_finish
        self.is_playing = False
        self._stop_requested = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def play(self, actions: List[Dict[str, Any]], loop_count: int = 1) -> bool:
        """
        Avvia la riproduzione in background.
        loop_count: numero di ripetizioni (<= 0 indica loop infinito).
        """
        if not actions:
            return False

        with self._lock:
            if self.is_playing:
                return False
            self.is_playing = True
            self._stop_requested = False
            self._thread = threading.Thread(
                target=self._playback_loop,
                args=(list(actions), loop_count),
                daemon=True
            )
            self._thread.start()
        return True

    def stop(self) -> None:
        """Richiede l'arresto immediato della macro."""
        self._stop_requested = True
        self.is_playing = False

    def _playback_loop(self, actions: List[Dict[str, Any]], loop_count: int) -> None:
        """Loop di esecuzione dei singoli step."""
        current_cycle = 0
        infinite = (loop_count <= 0)

        try:
            while not self._stop_requested:
                current_cycle += 1
                for step in actions:
                    if self._stop_requested:
                        break

                    delay = float(step.get("delay", 0.01))
                    # Sleep preciso
                    target_time = time.perf_counter() + delay
                    while time.perf_counter() < target_time and not self._stop_requested:
                        time.sleep(0.001)

                    if self._stop_requested:
                        break

                    self._execute_step(step)

                if not infinite and current_cycle >= loop_count:
                    break
        finally:
            self.is_playing = False
            if self.on_finish:
                self.on_finish()

    def _execute_step(self, step: Dict[str, Any]) -> None:
        """Esegue una singola azione registrata."""
        stype = step.get("type")

        if stype == "mouse_down":
            btn = step.get("button", "left")
            send_mouse_click(btn, action="down")

        elif stype == "mouse_up":
            btn = step.get("button", "left")
            send_mouse_click(btn, action="up")

        elif stype == "mouse_wheel":
            delta = step.get("delta", 120)
            send_mouse_wheel(delta)

        elif stype == "mouse_move":
            x = step.get("x")
            y = step.get("y")
            if x is not None and y is not None:
                ctypes.windll.user32.SetCursorPos(int(x), int(y))

        elif stype == "key_down":
            key = step.get("key", "")
            send_key_stroke(key, action="down")

        elif stype == "key_up":
            key = step.get("key", "")
            send_key_stroke(key, action="up")
