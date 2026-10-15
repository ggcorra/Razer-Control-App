"""
Modulo per la rimappatura avanzata dei tasti fisici del mouse.
Installa un hook a basso livello (WH_MOUSE_LL) per intercettare i pulsanti:
- Click Sinistro (WM_LBUTTONDOWN)
- Click Destro (WM_RBUTTONDOWN)
- Click Centrale (WM_MBUTTONDOWN)
- Tasto Laterale 1 / Indietro (WM_XBUTTONDOWN, XBUTTON1)
- Tasto Laterale 2 / Avanti (WM_XBUTTONDOWN, XBUTTON2)
- Rotellina (WM_MOUSEWHEEL)

Consente:
- Assegnazione di click alternativo (es. X1 -> Click Centrale)
- Combinazione di tasti (es. Ctrl + C, Alt + Tab)
- Attivazione di macro registrate
- Ripetizione continua (Rapid Fire) mentre il tasto fisico rimane premuto
- Ciclo del profilo DPI
"""

import time
import ctypes
import threading
from ctypes import wintypes
from typing import Dict, Any, Callable, Optional
from hardware.windows_hook import send_mouse_click, send_key_combination, send_mouse_wheel

# Costanti Hook Win32
WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
WM_MOUSEWHEEL = 0x020A

XBUTTON1 = 0x0001
XBUTTON2 = 0x0002
LLMHF_INJECTED = 0x00000001


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong)
    ]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32 = ctypes.windll.user32
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_ssize_t


class MouseRemapper:
    """
    Gestore della rimappatura dei tasti del mouse con soppressione e iniezione Win32.
    """

    def __init__(
        self,
        remapping_config: Optional[Dict[str, Any]] = None,
        on_dpi_cycle: Optional[Callable[[], None]] = None,
        on_macro_trigger: Optional[Callable[[str], None]] = None
    ):
        self.mappings: Dict[str, Any] = remapping_config or {}
        self.on_dpi_cycle = on_dpi_cycle
        self.on_macro_trigger = on_macro_trigger

        self._hook_handle: Optional[int] = None
        self._hook_proc_ref: Optional[HOOKPROC] = None
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._running = False

        # Stato per il rapid-fire mentre premuto
        self._rapid_fire_active: Dict[str, bool] = {}
        self._rapid_fire_threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def update_mappings(self, new_mappings: Dict[str, Any]) -> None:
        """Aggiorna la mappa dei pulsanti attivi."""
        with self._lock:
            self.mappings = dict(new_mappings)

    def start(self) -> bool:
        """Avvia l'hook globale in un thread separato con message loop Win32."""
        if self._running:
            return True

        self._running = True
        self._thread = threading.Thread(target=self._hook_worker, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        """Disinstalla l'hook e termina il thread di ascolto."""
        self._running = False
        with self._lock:
            # Ferma eventuali rapid-fire attivi
            for btn in list(self._rapid_fire_active.keys()):
                self._rapid_fire_active[btn] = False

        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT

        if self._hook_handle:
            ctypes.windll.user32.UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None

    def _hook_worker(self) -> None:
        """Esegue il message loop Win32 necessario per WH_MOUSE_LL."""
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        def low_level_mouse_proc(nCode: int, wParam: wintypes.WPARAM, lParam: wintypes.LPARAM) -> int:
            if nCode < 0:
                return ctypes.windll.user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

            info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents

            # Se l'evento è stato iniettato da noi tramite SendInput, lascialo passare subito
            if (info.flags & LLMHF_INJECTED) != 0:
                return ctypes.windll.user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

            # Riconoscimento tasto
            btn_key = None
            is_down = False
            is_up = False

            if wParam == WM_LBUTTONDOWN:
                btn_key, is_down = "button_left", True
            elif wParam == WM_LBUTTONUP:
                btn_key, is_up = "button_left", True
            elif wParam == WM_RBUTTONDOWN:
                btn_key, is_down = "button_right", True
            elif wParam == WM_RBUTTONUP:
                btn_key, is_up = "button_right", True
            elif wParam == WM_MBUTTONDOWN:
                btn_key, is_down = "button_middle", True
            elif wParam == WM_MBUTTONUP:
                btn_key, is_up = "button_middle", True
            elif wParam in (WM_XBUTTONDOWN, WM_XBUTTONUP):
                high_word = (info.mouseData >> 16) & 0xFFFF
                btn_key = "button_x1" if high_word == XBUTTON1 else "button_x2"
                is_down = (wParam == WM_XBUTTONDOWN)
                is_up = (wParam == WM_XBUTTONUP)

            if btn_key:
                handled = self._handle_button_event(btn_key, is_down, is_up)
                if handled:
                    return 1  # Sopprime l'evento nativo originale di Windows!

            return ctypes.windll.user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

        self._hook_proc_ref = HOOKPROC(low_level_mouse_proc)
        self._hook_handle = user32.SetWindowsHookExW(
            WH_MOUSE_LL,
            self._hook_proc_ref,
            None,
            0
        )

        if not self._hook_handle:
            self._running = False
            return

        msg = wintypes.MSG()
        while self._running:
            res = ctypes.windll.user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if res <= 0:
                break
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

        if self._hook_handle:
            ctypes.windll.user32.UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None

    def _handle_button_event(self, btn_key: str, is_down: bool, is_up: bool) -> bool:
        """Esegue l'azione rimappata per il pulsante premuto/rilasciato."""
        config = self.mappings.get(btn_key)
        if not config or config.get("type") == "default":
            return False  # Non rimappato, lascia passare

        action_type = config.get("type")

        # 1. Combinazione di tasti (es: Ctrl+C)
        if action_type == "key_combo":
            if is_down:
                keys = config.get("keys", [])
                threading.Thread(target=send_key_combination, args=(keys,), daemon=True).start()
            return True  # Soppresso l'evento mouse originale

        # 2. Click alternativo del mouse (es: X1 -> click centrale)
        elif action_type == "mouse_remap":
            target_btn = config.get("target_button", "left")
            if is_down:
                send_mouse_click(target_btn, action="down")
            elif is_up:
                send_mouse_click(target_btn, action="up")
            return True

        # 3. Ripetizione rapida (Rapid-Fire) finché tenuto premuto
        elif action_type == "rapid_fire":
            target_click = config.get("target_button", "left")
            interval_ms = max(10, int(config.get("interval_ms", 40)))

            if is_down:
                with self._lock:
                    self._rapid_fire_active[btn_key] = True
                    th = threading.Thread(
                        target=self._rapid_fire_loop,
                        args=(btn_key, target_click, interval_ms),
                        daemon=True
                    )
                    self._rapid_fire_threads[btn_key] = th
                    th.start()
            elif is_up:
                with self._lock:
                    self._rapid_fire_active[btn_key] = False
            return True

        # 4. Ciclo DPI
        elif action_type == "dpi_cycle":
            if is_down and self.on_dpi_cycle:
                threading.Thread(target=self.on_dpi_cycle, daemon=True).start()
            return True

        # 5. Esecuzione Macro
        elif action_type == "macro":
            macro_name = config.get("macro_name", "")
            if is_down and self.on_macro_trigger and macro_name:
                threading.Thread(target=self.on_macro_trigger, args=(macro_name,), daemon=True).start()
            return True

        return False

    def _rapid_fire_loop(self, btn_key: str, target_btn: str, interval_ms: int) -> None:
        """Loop di click ripetuti mentre il tasto fisico è tenuto premuto."""
        delay = interval_ms / 1000.0
        while self._running and self._rapid_fire_active.get(btn_key, False):
            send_mouse_click(target_btn, action="click")
            time.sleep(delay)
