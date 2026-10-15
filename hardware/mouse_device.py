"""
Modulo per la gestione della comunicazione diretta con il mouse Razer Viper V3 HyperSpeed.
Gestisce apertura, chiusura, invio report di controllo e gestione degli errori
(dispositivo assente, permessi di accesso, pacchetti non supportati).
"""

import time
import logging
from typing import Optional, Tuple, Dict, Any

try:
    import hid
except ImportError:
    hid = None

from .razer_protocol import (
    RAZER_VENDOR_ID,
    RAZER_VIPER_V3_HYPERSPEED_PID,
    CMD_CLASS_SYSTEM,
    CMD_CLASS_DPI,
    CMD_CLASS_POWER,
    CMD_ID_GET_BATTERY,
    CMD_ID_GET_CHARGING,
    CMD_ID_GET_DPI,
    CMD_ID_SET_DPI,
    CMD_ID_GET_POLLING_RATE,
    CMD_ID_SET_POLLING_RATE,
    POLLING_RATE_TO_BYTE,
    STATUS_SUCCESS,
    build_razer_report,
    parse_battery_response,
    parse_charging_response,
    parse_dpi_response,
    parse_polling_rate_response
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RazerDevice")


class DeviceError(Exception):
    """Eccezione base per errori del dispositivo."""
    pass


class DeviceNotFoundError(DeviceError):
    """Sollevata quando il mouse non viene rilevato sulle porte USB."""
    pass


class AccessDeniedError(DeviceError):
    """Sollevata quando l'interfaccia HID è bloccata da un altro processo o mancano i permessi."""
    pass


class ProtocolError(DeviceError):
    """Sollevata quando il protocollo hardware restituisce un errore."""
    pass


class RazerMouseDevice:
    """
    Rappresenta il mouse Razer Viper V3 HyperSpeed connesso tramite dongle USB a 2.4 GHz.
    Fornisce comandi atomici per DPI, Polling Rate, Batteria e monitoraggio continuo.
    """

    def __init__(self, vendor_id: int = RAZER_VENDOR_ID, product_id: int = RAZER_VIPER_V3_HYPERSPEED_PID):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.device_handle: Optional[Any] = None
        self.device_path: Optional[bytes] = None
        self.is_connected: bool = False
        self.product_name: str = "Razer Viper V3 HyperSpeed"
        self.simulated_mode: bool = False

    def connect(self) -> bool:
        """
        Cerca tra le interfacce HID collegate quella in grado di comunicare tramite Feature Report Razer.
        Ritorna True se la connessione ha successo, solleva eccezione altrimenti.
        """
        if hid is None:
            raise DeviceError("Modulo 'hidapi' non installato.")

        devices = hid.enumerate(self.vendor_id, self.product_id)
        if not devices:
            self.is_connected = False
            raise DeviceNotFoundError("Mouse Razer Viper V3 HyperSpeed non trovato. Assicurati che il dongle sia inserito.")

        # Cerchiamo tra tutte le interfacce disponibili quella compatibile
        last_error = None
        for dev_info in devices:
            path = dev_info.get("path")
            h = hid.device()
            try:
                h.open_path(path)
                # Verifica immediata con richiesta stato batteria
                test_report = build_razer_report(CMD_CLASS_POWER, CMD_ID_GET_BATTERY)
                h.send_feature_report(test_report)
                time.sleep(0.04)
                resp = h.get_feature_report(0x00, 91)
                if len(resp) >= 91 and resp[1] == STATUS_SUCCESS:
                    self.device_handle = h
                    self.device_path = path
                    self.is_connected = True
                    self.product_name = dev_info.get("product_string") or "Razer Viper V3 HyperSpeed"
                    logger.info(f"Connesso al dispositivo hardware con successo: {self.product_name}")
                    return True
                h.close()
            except Exception as e:
                h.close()
                last_error = e

        if last_error:
            # Se nessuna interfaccia ha risposto positivamente
            logger.warning(f"Impossibile agganciare l'endpoint di controllo: {last_error}")
            raise AccessDeniedError(
                f"Trovato dispositivo Razer ma l'endpoint HID è protetto o occupato da Razer Synapse: {last_error}"
            )

        raise DeviceError("Nessuna interfaccia HID Razer ha risposto al protocollo di controllo.")

    def disconnect(self) -> None:
        """Chiude in sicurezza l'handle HID del mouse."""
        if self.device_handle:
            try:
                self.device_handle.close()
            except Exception:
                pass
            self.device_handle = None
        self.is_connected = False

    def _transaction(self, report: bytes, delay_ms: float = 0.04) -> bytes:
        """Invia un feature report e legge la risposta a 91 byte in modo sincrono protetto."""
        if not self.is_connected or not self.device_handle:
            raise DeviceNotFoundError("Il dispositivo non è connesso.")

        try:
            self.device_handle.send_feature_report(report)
            time.sleep(delay_ms)
            response = self.device_handle.get_feature_report(0x00, 91)
            if not response or len(response) < 91:
                raise ProtocolError("Risposta del mouse incompleta o non valida.")
            return bytes(response)
        except Exception as e:
            logger.error(f"Errore durante transazione HID: {e}")
            self.disconnect()
            raise DeviceError(f"Errore di comunicazione hardware: {e}")

    # =========================================================================
    # BATTERIA E STATO ENERGETICO
    # =========================================================================

    def get_battery_status(self) -> Dict[str, Any]:
        """
        Legge il livello di carica e lo stato di alimentazione (in carica / batteria).
        Ritorna un dizionario con percentuale (0-100), stato di ricarica e valore raw.
        """
        report_batt = build_razer_report(CMD_CLASS_POWER, CMD_ID_GET_BATTERY)
        resp_batt = self._transaction(report_batt)
        batt_data = parse_battery_response(resp_batt)
        if not batt_data:
            raise ProtocolError("Impossibile interpretare la risposta della batteria dal mouse.")

        percentage, raw_val = batt_data

        # Stato di ricarica
        is_charging = False
        try:
            report_chg = build_razer_report(CMD_CLASS_POWER, CMD_ID_GET_CHARGING)
            resp_chg = self._transaction(report_chg)
            parsed_chg = parse_charging_response(resp_chg)
            if parsed_chg is not None:
                is_charging = parsed_chg
        except Exception as e:
            logger.debug(f"Impossibile leggere stato ricarica: {e}")

        return {
            "level": percentage,
            "raw": raw_val,
            "charging": is_charging,
            "connected": True
        }

    # =========================================================================
    # DPI (RISOLUZIONE SENSORE)
    # =========================================================================

    def get_dpi(self) -> Tuple[int, int]:
        """
        Legge la risoluzione DPI attuale hardware del sensore (DPI X, DPI Y).
        """
        report = build_razer_report(CMD_CLASS_DPI, CMD_ID_GET_DPI, 0x01, bytes([0x00]))
        resp = self._transaction(report)
        dpi = parse_dpi_response(resp)
        if not dpi:
            raise ProtocolError("Impossibile leggere i valori DPI correnti.")
        return dpi

    def set_dpi(self, dpi_x: int, dpi_y: Optional[int] = None) -> bool:
        """
        Configura la risoluzione DPI hardware del mouse (100 - 30000 DPI).
        Se dpi_y non è specificato, viene impostato uguale a dpi_x.
        """
        if dpi_y is None:
            dpi_y = dpi_x

        dpi_x = max(100, min(30000, int(dpi_x)))
        dpi_y = max(100, min(30000, int(dpi_y)))

        # Struttura argomenti per impostazione DPI: [0x00, X_hi, X_lo, Y_hi, Y_lo]
        args = bytes([
            0x00,
            (dpi_x >> 8) & 0xFF,
            dpi_x & 0xFF,
            (dpi_y >> 8) & 0xFF,
            dpi_y & 0xFF
        ])

        report = build_razer_report(CMD_CLASS_DPI, CMD_ID_SET_DPI, 0x07, args)
        resp = self._transaction(report)
        if resp[1] != STATUS_SUCCESS:
            raise ProtocolError(f"Scrittura DPI rifiutata dal mouse (Status: {resp[1]}).")
        return True

    # =========================================================================
    # POLLING RATE (FREQUENZA DI AGGIORNAMENTO USB)
    # =========================================================================

    def get_polling_rate(self) -> int:
        """
        Legge il polling rate hardware attuale (125, 250, 500, 1000 Hz).
        """
        report = build_razer_report(CMD_CLASS_SYSTEM, CMD_ID_GET_POLLING_RATE)
        resp = self._transaction(report)
        rate = parse_polling_rate_response(resp)
        if not rate:
            raise ProtocolError("Impossibile leggere il polling rate hardware.")
        return rate

    def set_polling_rate(self, rate_hz: int) -> bool:
        """
        Imposta il polling rate hardware (125, 250, 500, 1000 Hz).
        Viene applicato istantaneamente sul sensore.
        """
        if rate_hz not in POLLING_RATE_TO_BYTE:
            raise ValueError(f"Frequenza {rate_hz} Hz non supportata. Valori ammessi: 125, 250, 500, 1000.")

        byte_val = POLLING_RATE_TO_BYTE[rate_hz]
        args = bytes([byte_val])
        report = build_razer_report(CMD_CLASS_SYSTEM, CMD_ID_SET_POLLING_RATE, 0x01, args)
        resp = self._transaction(report)
        if resp[1] != STATUS_SUCCESS:
            raise ProtocolError(f"Impostazione Polling Rate rifiutata dal mouse (Status: {resp[1]}).")
        return True
