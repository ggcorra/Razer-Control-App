"""
Finestra principale dell'applicazione PySide6.
Coordina navigazione a schede, sincronizzazione hardware, gestione profili,
temi chiaro/scuro, hotkey globali e notifiche di sistema nella tray bar.
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QFrame, QStatusBar, QSystemTrayIcon,
    QMenu, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QAction

from config.settings_manager import SettingsManager
from hardware.mouse_device import RazerMouseDevice, DeviceError, DeviceNotFoundError, AccessDeniedError
from macro.autoclicker import AutoClicker
from macro.macro_recorder import MacroRecorder
from macro.macro_player import MacroPlayer
from macro.remapper import MouseRemapper
from macro.hotkey_manager import GlobalHotkeyManager

from .styles import DARK_THEME, LIGHT_THEME
from .dpi_view import DpiView
from .polling_view import PollingView
from .remap_view import RemapView
from .macro_view import MacroView
from .battery_view import BatteryView


class MainWindow(QMainWindow):
    """
    Finestra principale dell'applicazione Razer Controller.
    """

    battery_updated = Signal(int, bool, int)
    hw_status_updated = Signal(str, bool)

    def __init__(self, settings: SettingsManager, device: RazerMouseDevice):
        super().__init__()
        self.settings = settings
        self.device = device

        self.setWindowTitle("Razer Viper V3 HyperSpeed Control Center")
        self.resize(1020, 680)
        self.setMinimumSize(850, 580)

        # Inizializzazione motori macro e remapping
        self.autoclicker = AutoClicker(
            interval_ms=self.settings.data["autoclicker"]["interval_ms"],
            randomize=self.settings.data["autoclicker"]["randomize"],
            jitter_ms=self.settings.data["autoclicker"]["random_jitter_ms"],
            button=self.settings.data["autoclicker"]["button"],
            on_state_change=self._on_autoclicker_state_changed
        )
        self.macro_recorder = MacroRecorder(
            record_moves=False,
            on_event_recorded=self._on_macro_step_recorded
        )
        self.macro_player = MacroPlayer(on_finish=self._on_macro_play_finished)

        active_profile = self.settings.get_active_profile()
        self.remapper = MouseRemapper(
            remapping_config=active_profile.get("remapping", {}),
            on_dpi_cycle=self.cycle_next_profile,
            on_macro_trigger=self.play_macro_by_name
        )
        self.remapper.start()

        self.hotkey_mgr = GlobalHotkeyManager()

        # Configurazione interfaccia
        self._setup_ui()
        self._setup_tray()
        self._setup_hotkeys()

        # Timer periodico per stato batteria (ogni 30 secondi)
        self._battery_timer = QTimer(self)
        self._battery_timer.timeout.connect(self._poll_battery_hardware)
        self._battery_timer.start(30000)

        # Prima sincronizzazione hardware
        QTimer.singleShot(500, self._initial_hardware_sync)

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -------------------------------------------------------------
        # 1. SIDEBAR SINISTRA
        # -------------------------------------------------------------
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(0, 16, 0, 16)
        sb_layout.setSpacing(4)

        # Logo / Titolo Sidebar
        title_box = QVBoxLayout()
        title_box.setContentsMargins(18, 0, 18, 16)
        lbl_app = QLabel("RAZER CONTROL")
        lbl_app.setStyleSheet("font-size: 16px; font-weight: 800; color: #00FF66; letter-spacing: 1px;")
        lbl_sub = QLabel("Viper V3 HyperSpeed")
        lbl_sub.setStyleSheet("font-size: 11px; color: #777777; font-weight: 600;")
        title_box.addWidget(lbl_app)
        title_box.addWidget(lbl_sub)
        sb_layout.addLayout(title_box)

        # Pulsanti sezioni
        self.btn_nav_dpi = QPushButton("🎯  DPI & Profili")
        self.btn_nav_polling = QPushButton("⚡  Polling Rate")
        self.btn_nav_remap = QPushButton("🖱️  Rimappatura Tasti")
        self.btn_nav_macro = QPushButton("🎬  Macro & Autoclicker")
        self.btn_nav_battery = QPushButton("🔋  Batteria & Info")

        self.nav_buttons = [
            self.btn_nav_dpi,
            self.btn_nav_polling,
            self.btn_nav_remap,
            self.btn_nav_macro,
            self.btn_nav_battery
        ]

        for i, btn in enumerate(self.nav_buttons):
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, idx=i: self._switch_page(idx))
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        # Toggle Tema in fondo alla sidebar
        self.btn_theme_toggle = QPushButton("☀️ Tema Chiaro")
        self.btn_theme_toggle.setStyleSheet("""
            background-color: transparent; border: 1px solid #333333;
            border-radius: 6px; padding: 8px; margin: 12px; font-size: 12px;
        """)
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)
        sb_layout.addWidget(self.btn_theme_toggle)

        main_layout.addWidget(self.sidebar)

        # -------------------------------------------------------------
        # 2. CONTENUTO CENTRALE (Stacked Widget)
        # -------------------------------------------------------------
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Barra superiore (Top Bar)
        topbar = QFrame()
        topbar.setFixedHeight(50)
        topbar.setStyleSheet("background-color: #161616; border-bottom: 1px solid #242424;")
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(20, 0, 20, 0)

        self.lbl_conn_indicator = QLabel("● In Ricerca Hardware...")
        self.lbl_conn_indicator.setStyleSheet("color: #ffaa00; font-weight: bold; font-size: 13px;")
        tb_layout.addWidget(self.lbl_conn_indicator)

        tb_layout.addStretch()

        self.lbl_active_prof_badge = QLabel(f"Profilo: {self.settings.get_active_profile_name()}")
        self.lbl_active_prof_badge.setStyleSheet("""
            background-color: #242424; color: #00FF66;
            padding: 4px 12px; border-radius: 4px; font-weight: 600; font-size: 12px;
        """)
        tb_layout.addWidget(self.lbl_active_prof_badge)

        content_layout.addWidget(topbar)

        # Pagine dell'applicazione
        self.stack = QStackedWidget()

        self.page_dpi = DpiView()
        self.page_polling = PollingView()
        self.page_remap = RemapView()
        self.page_macro = MacroView()
        self.page_battery = BatteryView()

        self.stack.addWidget(self.page_dpi)
        self.stack.addWidget(self.page_polling)
        self.stack.addWidget(self.page_remap)
        self.stack.addWidget(self.page_macro)
        self.stack.addWidget(self.page_battery)

        content_layout.addWidget(self.stack)
        main_layout.addWidget(content_container, 1)

        # -------------------------------------------------------------
        # 3. STATUS BAR
        # -------------------------------------------------------------
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_status_device = QLabel("Dispositivo: Inizializzazione...")
        self.lbl_status_dpi = QLabel("DPI: 1600")
        self.lbl_status_rate = QLabel("Polling: 1000 Hz")
        self.status_bar.addWidget(self.lbl_status_device, 1)
        self.status_bar.addPermanentWidget(self.lbl_status_dpi)
        self.status_bar.addPermanentWidget(self.lbl_status_rate)

        # Connessione segnali delle viste
        self._connect_signals()

        # Attiva prima scheda e applica tema iniziale
        self._switch_page(0)
        self._apply_theme(self.settings.get_theme())

    def _setup_tray(self) -> None:
        """Inizializza l'icona nell'area di notifica di Windows."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        self.tray_icon.setToolTip("Razer Viper V3 HyperSpeed Controller")

        tray_menu = QMenu()
        show_action = QAction("Mostra Finestra", self)
        show_action.triggered.connect(self.showNormal)
        quit_action = QAction("Esci", self)
        quit_action.triggered.connect(QApplication.instance().quit)

        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()

    def _setup_hotkeys(self) -> None:
        """Configura le scorciatoie globali di Windows."""
        hotkeys = {
            self.settings.data["hotkeys"].get("autoclicker_toggle", "F6"): self.autoclicker.toggle,
            self.settings.data["hotkeys"].get("switch_profile", "F7"): self.cycle_next_profile,
            self.settings.data["hotkeys"].get("macro_record_toggle", "F9"): self._toggle_macro_record_hotkey,
            self.settings.data["hotkeys"].get("macro_play_toggle", "F10"): self._toggle_macro_play_hotkey,
        }
        self.hotkey_mgr.set_hotkeys(hotkeys)
        self.hotkey_mgr.start()

    def _connect_signals(self) -> None:
        # DPI View
        self.page_dpi.dpi_changed.connect(self._on_dpi_changed)
        self.page_dpi.profile_switched.connect(self._on_profile_selected)
        self.page_dpi.profile_created.connect(self._on_profile_created)
        self.page_dpi.profile_deleted.connect(self._on_profile_deleted)

        # Polling View
        self.page_polling.polling_rate_changed.connect(self._on_polling_rate_changed)

        # Remap View
        self.page_remap.remapping_updated.connect(self._on_remapping_updated)

        # Macro View
        self.page_macro.autoclicker_toggled.connect(self._on_ui_autoclicker_toggled)
        self.page_macro.autoclicker_config_changed.connect(self._on_autoclicker_config_changed)
        self.page_macro.macro_record_started.connect(self._on_macro_record_started)
        self.page_macro.macro_record_stopped.connect(self._on_macro_record_stopped)
        self.page_macro.macro_play_started.connect(self._on_macro_play_started)
        self.page_macro.macro_play_stopped.connect(self.macro_player.stop)
        self.page_macro.macro_saved.connect(self._on_macro_saved)
        self.page_macro.macro_deleted.connect(self._on_macro_deleted)

        # Battery View
        self.page_battery.refresh_requested.connect(self._poll_battery_hardware)
        self.battery_updated.connect(self.page_battery.update_battery)

    def _switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def _toggle_theme(self) -> None:
        current = self.settings.get_theme()
        new_theme = "light" if current == "dark" else "dark"
        self.settings.set_theme(new_theme)
        self._apply_theme(new_theme)

    def _apply_theme(self, theme: str) -> None:
        if theme == "light":
            self.setStyleSheet(LIGHT_THEME)
            self.btn_theme_toggle.setText("🌙 Tema Scuro")
        else:
            self.setStyleSheet(DARK_THEME)
            self.btn_theme_toggle.setText("☀️ Tema Chiaro")

    # -------------------------------------------------------------
    # SINCRONIZZAZIONE HARDWARE
    # -------------------------------------------------------------
    def _initial_hardware_sync(self) -> None:
        """Tenta la connessione fisica e applica il profilo iniziale."""
        try:
            self.device.connect()
            self.lbl_conn_indicator.setText("● Connesso Hardware (2.4 GHz HyperSpeed)")
            self.lbl_conn_indicator.setStyleSheet("color: #00FF66; font-weight: bold; font-size: 13px;")
            self.lbl_status_device.setText(f"Dispositivo: {self.device.product_name} (VID 1532, PID 00B8)")
            self.page_dpi.set_hardware_status("Protocollo: Connesso a livello hardware", True)
        except Exception as e:
            self.lbl_conn_indicator.setText("○ Dispositivo Non Connesso (Modalità Software)")
            self.lbl_conn_indicator.setStyleSheet("color: #ff6666; font-weight: bold; font-size: 13px;")
            self.lbl_status_device.setText(f"Stato: {e}")
            self.page_dpi.set_hardware_status(f"Non connesso ({e})", False)

        # Carica profili nella vista DPI
        all_profiles = list(self.settings.get_all_profiles().keys())
        active_name = self.settings.get_active_profile_name()
        self.page_dpi.set_profiles_list(all_profiles, active_name)

        # Applica impostazioni profilo corrente
        self._apply_profile_to_system(active_name)

        # Carica macro
        self.page_macro.set_macros_library(self.settings.get_macros())

        # Prima lettura batteria
        self._poll_battery_hardware()

    def _apply_profile_to_system(self, profile_name: str) -> None:
        """Applica DPI, Polling Rate e Rimappatura del profilo scelto."""
        self.settings.set_active_profile_name(profile_name)
        prof = self.settings.get_active_profile()

        dpi_val = prof.get("dpi", 1600)
        rate_val = prof.get("polling_rate", 1000)
        remap = prof.get("remapping", {})

        # 1. DPI
        self.page_dpi.set_dpi_value(dpi_val)
        self.lbl_status_dpi.setText(f"DPI: {dpi_val}")
        if self.device.is_connected:
            try:
                self.device.set_dpi(dpi_val)
            except Exception as e:
                print(f"[DPI] Errore applicazione hardware: {e}")

        # 2. Polling rate
        self.page_polling.set_polling_rate(rate_val)
        self.lbl_status_rate.setText(f"Polling: {rate_val} Hz")
        if self.device.is_connected:
            try:
                self.device.set_polling_rate(rate_val)
            except Exception as e:
                print(f"[Polling] Errore applicazione hardware: {e}")

        # 3. Rimappatura
        self.remapper.update_mappings(remap)
        macro_names = list(self.settings.get_macros().keys())
        self.page_remap.set_mappings(remap, macro_names)

        # Badge
        self.lbl_active_prof_badge.setText(f"Profilo: {profile_name}")

    def cycle_next_profile(self) -> None:
        """Scambia ciclicamente il profilo (chiamato da hotkey F7 o tasto mouse)."""
        profiles = list(self.settings.get_all_profiles().keys())
        if not profiles:
            return
        curr = self.settings.get_active_profile_name()
        idx = profiles.index(curr) if curr in profiles else 0
        next_idx = (idx + 1) % len(profiles)
        next_prof = profiles[next_idx]

        self._apply_profile_to_system(next_prof)
        self.page_dpi.profile_combo.blockSignals(True)
        self.page_dpi.profile_combo.setCurrentText(next_prof)
        self.page_dpi.profile_combo.blockSignals(False)

        # Notifica visiva Windows Tray
        if self.tray_icon:
            self.tray_icon.showMessage(
                "Profilo Razer Attivato",
                f"Passato a: {next_prof} (DPI {self.settings.get_active_profile().get('dpi')})",
                QSystemTrayIcon.Information,
                1500
            )

    def _poll_battery_hardware(self) -> None:
        """Legge lo stato della batteria dal mouse tramite feature report."""
        if not self.device.is_connected:
            # Tenta riconnessione rapida se disconnesso
            try:
                self.device.connect()
                self.lbl_conn_indicator.setText("● Connesso Hardware (2.4 GHz HyperSpeed)")
                self.lbl_conn_indicator.setStyleSheet("color: #00FF66; font-weight: bold; font-size: 13px;")
            except Exception:
                return

        try:
            status = self.device.get_battery_status()
            level = status["level"]
            charging = status["charging"]
            raw = status["raw"]

            self.battery_updated.emit(level, charging, raw)

            # Notifica batteria scarica (<20%)
            threshold = self.settings.data["notifications"].get("battery_threshold", 20)
            if level <= threshold and not charging and self.settings.data["notifications"].get("battery_low_warning", True):
                if self.tray_icon:
                    self.tray_icon.showMessage(
                        "Attenzione: Batteria Mouse Razer Scarica",
                        f"Il livello di carica del Razer Viper V3 è al {level}%. Collega il mouse per evitare interruzioni.",
                        QSystemTrayIcon.Warning,
                        5000
                    )
        except Exception as e:
            print(f"[Battery] Errore lettura batteria: {e}")

    # -------------------------------------------------------------
    # GESTORI EVENTI SCHEDE
    # -------------------------------------------------------------
    def _on_dpi_changed(self, value: int) -> None:
        self.settings.update_active_profile("dpi", value)
        self.lbl_status_dpi.setText(f"DPI: {value}")
        if self.device.is_connected:
            try:
                self.device.set_dpi(value)
                self.page_dpi.set_hardware_status(f"DPI {value} applicato al mouse!", True)
            except Exception as e:
                self.page_dpi.set_hardware_status(f"Errore hardware: {e}", False)

    def _on_profile_selected(self, name: str) -> None:
        self._apply_profile_to_system(name)

    def _on_profile_created(self, name: str, base_name: str) -> None:
        if self.settings.add_profile(name, base_name):
            all_profiles = list(self.settings.get_all_profiles().keys())
            self.page_dpi.set_profiles_list(all_profiles, name)
            self._apply_profile_to_system(name)

    def _on_profile_deleted(self, name: str) -> None:
        if self.settings.delete_profile(name):
            all_profiles = list(self.settings.get_all_profiles().keys())
            active = self.settings.get_active_profile_name()
            self.page_dpi.set_profiles_list(all_profiles, active)
            self._apply_profile_to_system(active)

    def _on_polling_rate_changed(self, rate_hz: int) -> None:
        self.settings.update_active_profile("polling_rate", rate_hz)
        self.lbl_status_rate.setText(f"Polling: {rate_hz} Hz")
        if self.device.is_connected:
            try:
                self.device.set_polling_rate(rate_hz)
                self.page_polling.set_hardware_status(f"Frequenza {rate_hz} Hz applicata al dispositivo con successo!", True)
            except Exception as e:
                self.page_polling.set_hardware_status(f"Errore applicazione hardware: {e}", False)

    def _on_remapping_updated(self, mappings: dict) -> None:
        self.settings.update_active_profile("remapping", mappings)
        self.remapper.update_mappings(mappings)

    # Autoclicker
    def _on_ui_autoclicker_toggled(self, active: bool) -> None:
        if active:
            self.autoclicker.start()
        else:
            self.autoclicker.stop()

    def _on_autoclicker_state_changed(self, active: bool) -> None:
        # Metodo invocato dal thread dell'autoclicker
        QTimer.singleShot(0, lambda: self.page_macro.set_autoclicker_active(active))

    def _on_autoclicker_config_changed(self, cfg: dict) -> None:
        self.autoclicker.set_config(
            interval_ms=cfg["interval_ms"],
            randomize=cfg["randomize"],
            jitter_ms=cfg["random_jitter_ms"],
            button=cfg["button"]
        )
        self.settings.data["autoclicker"].update(cfg)
        self.settings.save()

    # Macro
    def _on_macro_record_started(self, record_moves: bool) -> None:
        self.macro_recorder.record_moves = record_moves
        self.macro_recorder.start()

    def _on_macro_record_stopped(self) -> None:
        actions = self.macro_recorder.stop()
        self.page_macro.set_steps(actions)

    def _on_macro_step_recorded(self, step: dict) -> None:
        QTimer.singleShot(0, lambda: self.page_macro.append_recorded_step(step))

    def _on_macro_play_started(self, macro_name: str, loop_count: int) -> None:
        steps = self.page_macro.current_steps
        self.macro_player.play(steps, loop_count)

    def _on_macro_play_finished(self) -> None:
        QTimer.singleShot(0, lambda: self.page_macro.set_playing_state(False))

    def _on_macro_saved(self, name: str, macro_obj: dict) -> None:
        self.settings.save_macro(name, macro_obj)
        self.page_macro.set_macros_library(self.settings.get_macros(), select_name=name)
        # Aggiorna anche la lista macro disponibile nella rimappatura tasti
        self.page_remap.available_macros = list(self.settings.get_macros().keys())

    def _on_macro_deleted(self, name: str) -> None:
        self.settings.delete_macro(name)
        self.page_macro.set_macros_library(self.settings.get_macros())
        self.page_remap.available_macros = list(self.settings.get_macros().keys())

    def play_macro_by_name(self, name: str) -> None:
        """Esegue una macro registrata richiamata da un tasto rimappato."""
        macros = self.settings.get_macros()
        if name in macros:
            actions = macros[name].get("actions", [])
            loops = macros[name].get("loop_count", 1)
            self.macro_player.play(actions, loops)

    def _toggle_macro_record_hotkey(self) -> None:
        QTimer.singleShot(0, self.page_macro._on_record_btn_clicked)

    def _toggle_macro_play_hotkey(self) -> None:
        QTimer.singleShot(0, self.page_macro._on_play_btn_clicked)

    def closeEvent(self, event) -> None:
        """Minimizza nella system tray invece di chiudere bruscamente se desiderato."""
        reply = QMessageBox.question(
            self, "Chiusura Applicazione",
            "Vuoi minimizzare l'app nell'area di notifica (le macro, l'autoclicker e la rimappatura continueranno a funzionare) o uscire completamente?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            event.ignore()
            self.hide()
            if self.tray_icon:
                self.tray_icon.showMessage(
                    "Razer Controller in Background",
                    "L'app continua a funzionare nella barra delle applicazioni.",
                    QSystemTrayIcon.Information,
                    2000
                )
        elif reply == QMessageBox.No:
            # Arresto thread
            self.remapper.stop()
            self.hotkey_mgr.stop()
            self.autoclicker.stop()
            self.macro_player.stop()
            self.device.disconnect()
            event.accept()
        else:
            event.ignore()
