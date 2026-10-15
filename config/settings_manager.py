"""
Modulo per la gestione della configurazione e persistenza dei dati.
Salva e ricarica profili, impostazioni DPI, polling rate, rimappatura, macro e preferenze UI in formato JSON.
"""

import json
import os
from typing import Any, Dict, List

DEFAULT_SETTINGS: Dict[str, Any] = {
    "theme": "dark",  # "dark" oppure "light"
    "active_profile": "Gaming",
    "profiles": {
        "Gaming": {
            "dpi": 1600,
            "dpi_stages": [400, 800, 1600, 3200, 6400],
            "polling_rate": 1000,
            "remapping": {
                "button_left": {"type": "default", "action": "left_click"},
                "button_right": {"type": "default", "action": "right_click"},
                "button_middle": {"type": "default", "action": "middle_click"},
                "button_x1": {"type": "default", "action": "back"},
                "button_x2": {"type": "default", "action": "forward"},
                "button_dpi": {"type": "dpi_cycle", "action": "cycle"}
            }
        },
        "Lavoro": {
            "dpi": 800,
            "dpi_stages": [400, 800, 1200, 1600],
            "polling_rate": 500,
            "remapping": {
                "button_left": {"type": "default", "action": "left_click"},
                "button_right": {"type": "default", "action": "right_click"},
                "button_middle": {"type": "default", "action": "middle_click"},
                "button_x1": {"type": "key_combo", "keys": ["ctrl", "c"], "label": "Copia"},
                "button_x2": {"type": "key_combo", "keys": ["ctrl", "v"], "label": "Incolla"},
                "button_dpi": {"type": "dpi_cycle", "action": "cycle"}
            }
        }
    },
    "autoclicker": {
        "interval_ms": 50,
        "randomize": True,
        "random_jitter_ms": 10,
        "button": "left",  # "left", "right", "middle"
        "toggle_hotkey": "F6"
    },
    "hotkeys": {
        "switch_profile": "F7",
        "autoclicker_toggle": "F6",
        "macro_record_toggle": "F9",
        "macro_play_toggle": "F10"
    },
    "macros": {
        "Esempio Rapid Fire": {
            "name": "Esempio Rapid Fire",
            "loop_count": 5,
            "actions": [
                {"type": "mouse_down", "button": "left", "delay": 0.05},
                {"type": "mouse_up", "button": "left", "delay": 0.05}
            ]
        }
    },
    "notifications": {
        "battery_low_warning": True,
        "battery_threshold": 20
    }
}


class SettingsManager:
    """
    Gestore della configurazione su file JSON locale.
    Salva e carica in modo sicuro con fallback automatico ai valori di default.
    """

    def __init__(self, config_path: str = None):
        if config_path is None:
            # Percorso standard nella cartella dell'utente / applicazione
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_path = os.path.join(base_dir, "config.json")
        else:
            self.config_path = config_path

        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Carica le impostazioni dal file JSON. Se inesistente o corrotto, carica i default."""
        if not os.path.exists(self.config_path):
            self.data = dict(DEFAULT_SETTINGS)
            self.save()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Unione intelligente per mantenere chiavi nuove se la configurazione è di una versione precedente
                self.data = dict(DEFAULT_SETTINGS)
                self._deep_update(self.data, loaded)
        except Exception as e:
            print(f"[SettingsManager] Errore caricamento configurazione ({e}). Caricamento default.")
            self.data = dict(DEFAULT_SETTINGS)
            self.save()

    def save(self) -> None:
        """Salva lo stato corrente delle impostazioni su file JSON."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[SettingsManager] Errore salvataggio configurazione: {e}")

    def _deep_update(self, base: dict, update: dict) -> None:
        """Aggiorna ricorsivamente il dizionario base con i valori di update."""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    # Metodi di accesso rapido
    def get_theme(self) -> str:
        return self.data.get("theme", "dark")

    def set_theme(self, theme: str) -> None:
        self.data["theme"] = theme
        self.save()

    def get_active_profile_name(self) -> str:
        return self.data.get("active_profile", "Gaming")

    def set_active_profile_name(self, name: str) -> None:
        if name in self.data.get("profiles", {}):
            self.data["active_profile"] = name
            self.save()

    def get_active_profile(self) -> Dict[str, Any]:
        name = self.get_active_profile_name()
        return self.data.get("profiles", {}).get(name, DEFAULT_SETTINGS["profiles"]["Gaming"])

    def update_active_profile(self, key: str, value: Any) -> None:
        name = self.get_active_profile_name()
        if name in self.data.get("profiles", {}):
            self.data["profiles"][name][key] = value
            self.save()

    def get_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        return self.data.get("profiles", {})

    def add_profile(self, name: str, base_on: str = "Gaming") -> bool:
        if name in self.data["profiles"]:
            return False
        base = self.data["profiles"].get(base_on, DEFAULT_SETTINGS["profiles"]["Gaming"])
        self.data["profiles"][name] = json.loads(json.dumps(base))
        self.data["active_profile"] = name
        self.save()
        return True

    def delete_profile(self, name: str) -> bool:
        if name in self.data["profiles"] and len(self.data["profiles"]) > 1:
            del self.data["profiles"][name]
            if self.data["active_profile"] == name:
                self.data["active_profile"] = next(iter(self.data["profiles"]))
            self.save()
            return True
        return False

    def get_macros(self) -> Dict[str, Any]:
        return self.data.get("macros", {})

    def save_macro(self, name: str, macro_data: dict) -> None:
        if "macros" not in self.data:
            self.data["macros"] = {}
        self.data["macros"][name] = macro_data
        self.save()

    def delete_macro(self, name: str) -> bool:
        if "macros" in self.data and name in self.data["macros"]:
            del self.data["macros"][name]
            self.save()
            return True
        return False
