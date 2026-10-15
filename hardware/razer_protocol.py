"""
Modulo di definizione del protocollo hardware USB/HID per periferiche Razer.
Implementa la struttura a 90 byte conforme al protocollo OpenRazer:
- Header con Status, Transaction ID, Remaining Packets, Protocol Type, Data Size
- Command Class e Command ID
- Argomenti (80 byte)
- Checksum XOR (byte 2..87) e byte di chiusura
"""

from typing import Tuple, Optional

# Identificativi USB hardware per Razer Viper V3 HyperSpeed
RAZER_VENDOR_ID = 0x1532
RAZER_VIPER_V3_HYPERSPEED_PID = 0x00B8

# Classi di comando Razer
CMD_CLASS_SYSTEM = 0x00       # Polling rate, modalità operative
CMD_CLASS_DPI = 0x04          # Risoluzione sensore (DPI X/Y, stadi)
CMD_CLASS_POWER = 0x07        # Batteria, ricarica, stato alimentazione

# ID comando specifici
CMD_ID_GET_BATTERY = 0x80     # Lettura livello batteria
CMD_ID_GET_CHARGING = 0x84    # Lettura stato di ricarica
CMD_ID_GET_DPI = 0x85         # Lettura DPI corrente
CMD_ID_SET_DPI = 0x05         # Scrittura DPI corrente
CMD_ID_GET_POLLING_RATE = 0x85  # Lettura polling rate
CMD_ID_SET_POLLING_RATE = 0x05  # Scrittura polling rate

# Mappatura polling rate: Hz -> byte hardware
POLLING_RATE_TO_BYTE = {
    1000: 0x01,
    500: 0x02,
    250: 0x04,
    125: 0x08
}

BYTE_TO_POLLING_RATE = {
    0x01: 1000,
    0x02: 500,
    0x04: 250,
    0x08: 125
}

# Codici di stato risposta Razer
STATUS_NEW = 0x00
STATUS_BUSY = 0x01
STATUS_SUCCESS = 0x02
STATUS_FAILURE = 0x03
STATUS_TIMEOUT = 0x04
STATUS_NOT_SUPPORTED = 0x05


def calculate_crc(report_bytes: bytearray) -> int:
    """
    Calcola il checksum XOR sui byte da indice 2 fino a 87 inclusi.
    Questo rispetta lo standard hardware Razer.
    """
    crc = 0
    for b in report_bytes[2:88]:
        crc ^= b
    return crc


def build_razer_report(cmd_class: int, cmd_id: int, data_size: int = 0, args: bytes = b"") -> bytes:
    """
    Costruisce il payload di 90 byte per il comando Razer.
    Ritorna 91 byte totali (incluso il Report ID 0x00 iniziale per Windows HID Feature Report).
    """
    report = bytearray(90)
    report[0] = STATUS_NEW     # Status iniziale
    report[1] = 0x1F           # Transaction ID convenzionale
    report[2] = 0x00           # Remaining packets (Big Endian)
    report[3] = 0x00
    report[4] = 0x00           # Protocol type
    report[5] = data_size      # Lunghezza dati validi negli argomenti
    report[6] = cmd_class      # Classe del comando
    report[7] = cmd_id         # Identificativo del comando

    if args:
        length = min(len(args), 80)
        report[8:8 + length] = args[:length]

    # Calcolo CRC
    report[88] = calculate_crc(report)
    report[89] = 0x00          # Byte di riserva

    # Su Windows, Set/GetFeatureReport richiede che il primo byte sia il Report ID (0x00)
    return bytes([0x00]) + bytes(report)


def parse_battery_response(response: bytes) -> Optional[Tuple[int, int]]:
    """
    Decodifica la risposta del comando batteria (Classe 0x07, ID 0x80).
    Ritorna (percentuale 0-100, valore_raw 0-255) oppure None in caso di errore.
    """
    # response ha 91 byte (incluso report ID)
    if len(response) < 91:
        return None

    status = response[1]  # status nel report a 90 byte (offset 1 se c'è report ID)
    if status != STATUS_SUCCESS:
        return None

    raw_val = response[10]  # Argomento 1 (offset 8 + 1 nel payload + 1 per Report ID)
    percentage = round((raw_val / 255.0) * 100)
    percentage = max(0, min(100, percentage))
    return percentage, raw_val


def parse_charging_response(response: bytes) -> Optional[bool]:
    """
    Decodifica la risposta dello stato di ricarica (Classe 0x07, ID 0x84).
    Ritorna True se in carica, False se a batteria, None se non supportato.
    """
    if len(response) < 91:
        return None

    status = response[1]
    if status != STATUS_SUCCESS:
        return None

    is_charging = response[10] == 1
    return is_charging


def parse_dpi_response(response: bytes) -> Optional[Tuple[int, int]]:
    """
    Decodifica la risposta DPI (Classe 0x04, ID 0x85).
    Ritorna una tupla (dpi_x, dpi_y).
    """
    if len(response) < 91:
        return None

    status = response[1]
    if status != STATUS_SUCCESS:
        return None

    dpi_x = (response[10] << 8) | response[11]
    dpi_y = (response[12] << 8) | response[13]
    return dpi_x, dpi_y


def parse_polling_rate_response(response: bytes) -> Optional[int]:
    """
    Decodifica la risposta del polling rate (Classe 0x00, ID 0x85).
    Ritorna il polling rate in Hz (125, 250, 500, 1000).
    """
    if len(response) < 91:
        return None

    status = response[1]
    if status != STATUS_SUCCESS:
        return None

    rate_byte = response[9]
    return BYTE_TO_POLLING_RATE.get(rate_byte, 1000)
