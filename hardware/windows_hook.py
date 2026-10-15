"""
Modulo di integrazione nativa con le API di Windows (Win32 / ctypes).
Fornisce iniezione ad alte prestazioni tramite SendInput, simulazione click/tasti,
e benchmark in tempo reale del Polling Rate misurando gli eventi del mouse.
"""

import ctypes
import time
from ctypes import wintypes
from typing import Optional, Callable

# Definizioni costanti Win32
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# Eventi mouse
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000

XBUTTON1 = 0x0001
XBUTTON2 = 0x0002

# Eventi tastiera
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# Parametri di sistema
SPI_GETMOUSESPEED = 0x0070
SPI_SETMOUSESPEED = 0x0071
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02


# Strutture Ctypes per SendInput
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong)
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong)
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD)
    ]


class DUMMYUNIONNAME(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT)
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", DUMMYUNIONNAME)
    ]


# Mappatura tasti virtuali comuni
VK_MAP = {
    "ctrl": 0x11,
    "shift": 0x10,
    "alt": 0x12,
    "win": 0x5B,
    "tab": 0x09,
    "enter": 0x0D,
    "esc": 0x1B,
    "space": 0x20,
    "backspace": 0x08,
    "c": 0x43,
    "v": 0x56,
    "x": 0x58,
    "z": 0x5A,
    "y": 0x59,
    "a": 0x41,
    "s": 0x53,
    "w": 0x57,
    "d": 0x44,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B
}


def send_mouse_click(button: str = "left", action: str = "click") -> None:
    """
    Invia un click mouse sintetico nativo tramite Win32 SendInput.
    button: 'left', 'right', 'middle', 'x1', 'x2'
    action: 'click', 'down', 'up'
    """
    flags_down = 0
    flags_up = 0
    data = 0

    if button == "left":
        flags_down = MOUSEEVENTF_LEFTDOWN
        flags_up = MOUSEEVENTF_LEFTUP
    elif button == "right":
        flags_down = MOUSEEVENTF_RIGHTDOWN
        flags_up = MOUSEEVENTF_RIGHTUP
    elif button == "middle":
        flags_down = MOUSEEVENTF_MIDDLEDOWN
        flags_up = MOUSEEVENTF_MIDDLEUP
    elif button == "x1":
        flags_down = MOUSEEVENTF_XDOWN
        flags_up = MOUSEEVENTF_XUP
        data = XBUTTON1
    elif button == "x2":
        flags_down = MOUSEEVENTF_XDOWN
        flags_up = MOUSEEVENTF_XUP
        data = XBUTTON2

    inputs = []

    if action in ("down", "click"):
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.mi.dwFlags = flags_down
        inp.mi.mouseData = data
        inputs.append(inp)

    if action in ("up", "click"):
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.mi.dwFlags = flags_up
        inp.mi.mouseData = data
        inputs.append(inp)

    if inputs:
        n = len(inputs)
        arr = (INPUT * n)(*inputs)
        ctypes.windll.user32.SendInput(n, arr, ctypes.sizeof(INPUT))


def send_mouse_wheel(delta: int = 120) -> None:
    """Invia scroll verticale della rotellina (+120 = su, -120 = giù)."""
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.mi.dwFlags = MOUSEEVENTF_WHEEL
    inp.mi.mouseData = delta
    arr = (INPUT * 1)(inp)
    ctypes.windll.user32.SendInput(1, arr, ctypes.sizeof(INPUT))


def send_key_stroke(key_str: str, action: str = "press") -> None:
    """Invia pressione/rilascio di un tasto da tastiera."""
    key_lower = key_str.lower()
    vk = VK_MAP.get(key_lower)
    if not vk:
        if len(key_str) == 1:
            vk = ord(key_str.upper())
        else:
            return

    inputs = []
    if action in ("down", "press"):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ki.wVk = vk
        inputs.append(inp)

    if action in ("up", "press"):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ki.wVk = vk
        inp.ki.dwFlags = KEYEVENTF_KEYUP
        inputs.append(inp)

    if inputs:
        n = len(inputs)
        arr = (INPUT * n)(*inputs)
        ctypes.windll.user32.SendInput(n, arr, ctypes.sizeof(INPUT))


def send_key_combination(keys: list) -> None:
    """Invia una combinazione simultanea di tasti (es: ['ctrl', 'c'])."""
    vk_list = []
    for k in keys:
        vk = VK_MAP.get(k.lower())
        if not vk and len(k) == 1:
            vk = ord(k.upper())
        if vk:
            vk_list.append(vk)

    # Premi in sequenza
    for vk in vk_list:
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ki.wVk = vk
        arr = (INPUT * 1)(inp)
        ctypes.windll.user32.SendInput(1, arr, ctypes.sizeof(INPUT))

    time.sleep(0.01)

    # Rilascia in ordine inverso
    for vk in reversed(vk_list):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ki.wVk = vk
        inp.ki.dwFlags = KEYEVENTF_KEYUP
        arr = (INPUT * 1)(inp)
        ctypes.windll.user32.SendInput(1, arr, ctypes.sizeof(INPUT))


def get_windows_pointer_speed() -> int:
    """Legge la velocità del puntatore di Windows (1..20, default 10)."""
    speed = wintypes.DWORD()
    ctypes.windll.user32.SystemParametersInfoW(
        SPI_GETMOUSESPEED, 0, ctypes.byref(speed), 0
    )
    return speed.value


def set_windows_pointer_speed(speed: int) -> bool:
    """Imposta la velocità del puntatore a livello Windows (1..20)."""
    speed = max(1, min(20, speed))
    res = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETMOUSESPEED, 0, ctypes.c_void_p(speed), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
    )
    return bool(res)
