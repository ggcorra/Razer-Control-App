"""
Pacchetto per la gestione di macro, automazioni, autoclicker, rimappatura tasti e hotkey globali.
"""

from .autoclicker import AutoClicker
from .macro_recorder import MacroRecorder
from .macro_player import MacroPlayer
from .remapper import MouseRemapper
from .hotkey_manager import GlobalHotkeyManager

__all__ = [
    "AutoClicker",
    "MacroRecorder",
    "MacroPlayer",
    "MouseRemapper",
    "GlobalHotkeyManager"
]
