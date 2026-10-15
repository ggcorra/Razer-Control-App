"""
Modulo per la registrazione di macro avanzate.
Cattura click del mouse, coordinate di spostamento e battute da tastiera,
memorizzando i ritardi relativi tra ciascun evento.
"""

import time
import threading
from typing import List, Dict, Any, Callable, Optional

try:
    from pynput import mouse, keyboard
except ImportError:
    mouse = None
    keyboard = None


class MacroRecorder:
    """
    Registratore di macro multi-sorgente (mouse e tastiera) ad alta fedeltà.
    """

    def __init__(self, record_moves: bool = False, on_event_recorded: Optional[Callable[[dict], None]] = None):
        self.record_moves = record_moves
        self.on_event_recorded = on_event_recorded

        self.is_recording = False
        self.events: List[Dict[str, Any]] = []
        self._last_time = 0.0
        self._mouse_listener: Optional[Any] = None
        self._keyboard_listener: Optional[Any] = None
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Inizia la sessione di registrazione azzerando la lista corrente."""
        if mouse is None or keyboard is None:
            return False

        with self._lock:
            self.events = []
            self.is_recording = True
            self._last_time = time.perf_counter()

            # Avvio listener mouse
            self._mouse_listener = mouse.Listener(
                on_click=self._on_mouse_click,
                on_move=self._on_mouse_move if self.record_moves else None,
                on_scroll=self._on_mouse_scroll
            )
            self._mouse_listener.start()

            # Avvio listener tastiera
            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            self._keyboard_listener.start()

        return True

    def stop(self) -> List[Dict[str, Any]]:
        """Ferma la registrazione e restituisce la sequenza di eventi registrati."""
        with self._lock:
            if not self.is_recording:
                return list(self.events)

            self.is_recording = False
            if self._mouse_listener:
                self._mouse_listener.stop()
                self._mouse_listener = None

            if self._keyboard_listener:
                self._keyboard_listener.stop()
                self._keyboard_listener = None

            return list(self.events)

    def _record_action(self, action: Dict[str, Any]) -> None:
        """Calcola il ritardo relativo e memorizza l'evento."""
        now = time.perf_counter()
        delta = round(now - self._last_time, 4)
        self._last_time = now

        action["delay"] = max(0.001, delta)
        with self._lock:
            self.events.append(action)

        if self.on_event_recorded:
            self.on_event_recorded(action)

    def _on_mouse_click(self, x: int, y: int, button: Any, pressed: bool) -> None:
        if not self.is_recording:
            return

        b_name = "left"
        if button == mouse.Button.right:
            b_name = "right"
        elif button == mouse.Button.middle:
            b_name = "middle"
        elif button == mouse.Button.x1:
            b_name = "x1"
        elif button == mouse.Button.x2:
            b_name = "x2"

        action_type = "mouse_down" if pressed else "mouse_up"
        self._record_action({
            "type": action_type,
            "button": b_name,
            "x": int(x),
            "y": int(y)
        })

    def _on_mouse_move(self, x: int, y: int) -> None:
        if not self.is_recording:
            return
        # Throttle dei movimenti per non sovraccaricare la sequenza
        now = time.perf_counter()
        if now - self._last_time < 0.02:  # max 50 sample/sec per movimento
            return

        self._record_action({
            "type": "mouse_move",
            "x": int(x),
            "y": int(y)
        })

    def _on_mouse_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        if not self.is_recording:
            return
        self._record_action({
            "type": "mouse_wheel",
            "delta": 120 if dy > 0 else -120,
            "x": int(x),
            "y": int(y)
        })

    def _on_key_press(self, key: Any) -> None:
        if not self.is_recording:
            return
        key_str = self._key_to_str(key)
        self._record_action({
            "type": "key_down",
            "key": key_str
        })

    def _on_key_release(self, key: Any) -> None:
        if not self.is_recording:
            return
        key_str = self._key_to_str(key)
        self._record_action({
            "type": "key_up",
            "key": key_str
        })

    def _key_to_str(self, key: Any) -> str:
        if hasattr(key, "name") and key.name:
            return str(key.name).lower()
        if hasattr(key, "char") and key.char:
            return str(key.char).lower()
        return str(key).replace("Key.", "").lower()
