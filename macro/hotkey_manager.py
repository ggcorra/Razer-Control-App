"""
Modulo per la gestione di scorciatoie da tastiera globali (Global Hotkeys).
Funziona in background a livello di sistema operativo Windows anche con l'app minimizzata.
"""

import threading
from typing import Dict, Callable, Optional

try:
    from pynput import keyboard
except ImportError:
    keyboard = None


class GlobalHotkeyManager:
    """
    Gestore di hotkey globali con supporto per combinazioni (es. <ctrl>+<alt>+p, <f6>, <f7>).
    """

    def __init__(self):
        self._hotkey_listener: Optional[Any] = None
        self._handlers: Dict[str, Callable[[], None]] = {}
        self._running = False
        self._lock = threading.Lock()

    def set_hotkeys(self, hotkey_dict: Dict[str, Callable[[], None]]) -> bool:
        """
        Registra una mappa di hotkey -> callback.
        Esempio: {'<f6>': on_autoclicker_toggle, '<f7>': on_switch_profile}
        """
        with self._lock:
            self._handlers = dict(hotkey_dict)

        if self._running:
            self.stop()
            self.start()
        return True

    def start(self) -> bool:
        """Avvia l'ascolto delle hotkey globali."""
        if keyboard is None:
            return False

        with self._lock:
            if self._running or not self._handlers:
                return False

            # Conversione formato per pynput (es. "F6" -> "<f6>")
            formatted = {}
            for k, cb in self._handlers.items():
                fmt_key = k.strip().lower()
                if not fmt_key.startswith("<") and not fmt_key.endswith(">"):
                    fmt_key = f"<{fmt_key}>"
                formatted[fmt_key] = cb

            try:
                self._hotkey_listener = keyboard.GlobalHotKeys(formatted)
                self._hotkey_listener.start()
                self._running = True
                return True
            except Exception as e:
                print(f"[HotkeyManager] Errore avvio hotkey: {e}")
                self._running = False
                return False

    def stop(self) -> None:
        """Ferma l'ascolto delle hotkey globali."""
        with self._lock:
            if self._hotkey_listener:
                try:
                    self._hotkey_listener.stop()
                except Exception:
                    pass
                self._hotkey_listener = None
            self._running = False
