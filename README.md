# Razer Viper V3 HyperSpeed - Controller Desktop (Python & PySide6)

Applicazione desktop completa progettata per Windows 11 per il controllo avanzato del mouse **Razer Viper V3 HyperSpeed** (connessione wireless 2.4 GHz tramite dongle USB HyperSpeed).

---

## 📋 Indice dei Moduli e Architettura del Codice

Il progetto è suddiviso in moduli indipendenti e riutilizzabili:

```
razer_controller/
├── main.py                     # Entry point applicativo, gestione High-DPI e avvio PySide6
├── requirements.txt            # Dipendenze Python necessarie
├── settings.json               # File locale salvataggio configurazioni, profili e macro
├── config/
│   ├── __init__.py
│   └── settings_manager.py     # Gestore persistenza JSON, gestione profili e fallback
├── hardware/
│   ├── __init__.py
│   ├── razer_protocol.py       # Pacchetti da 90 byte Razer, calcolo checksum CRC XOR e parser
│   ├── mouse_device.py         # Comunicazione HID Feature Report, gestione errori e connessione
│   └── windows_hook.py         # Win32 SendInput nativo ad alte prestazioni e benchmark
├── macro/
│   ├── __init__.py
│   ├── autoclicker.py          # Autoclicker multi-thread ad alta precisione con jitter
│   ├── macro_recorder.py       # Registratore eventi mouse/tastiera con timestamp precisi
│   ├── macro_player.py         # Riproduttore sequenze con loop infinito o contato
│   ├── remapper.py             # Hook a basso livello WH_MOUSE_LL per soppressione e rimappatura
│   └── hotkey_manager.py       # Scorciatoie globali Windows (funzionano in background)
└── interface/
    ├── __init__.py
    ├── styles.py               # Fogli di stile QSS per Tema Scuro e Chiaro (accenti Razer #00FF66)
    ├── main_window.py          # Finestra principale con navigazione a schede e System Tray
    ├── dpi_view.py             # Slider, spinbox numerico, preset rapidi e profili (Gaming, Lavoro)
    ├── polling_view.py         # Selezione 125/250/500/1000 Hz e test benchmark in tempo reale
    ├── remap_view.py           # Configurazione tasti fisici, combinazioni tastiera e rapid-fire
    ├── macro_view.py           # Pannello autoclicker, libreria macro ed editor temporale
    └── battery_view.py         # Visualizzazione livello batteria, ricarica e notifiche Windows
```

---

## 🛠️ Librerie Utilizzate e Motivazioni Tecniche

| Libreria | Scopo Tecnico | Perché è stata scelta |
| :--- | :--- | :--- |
| **PySide6** | Interfaccia grafica (GUI) | Framework Qt ufficiale per Python. Garantisce grafica fluida, supporto High-DPI su Windows 11, icone nella System Tray, notifiche native e architettura robusta Signal/Slot. |
| **hidapi** | Comunicazione USB HID | Consente l'invio e la ricezione diretta di **Feature Reports HID** a 90 byte al dongle wireless del mouse Razer (VID `0x1532`, PID `0x00B8`), bypassando la necessità di driver complessi in modalità utente. |
| **pynput** | Registrazione Macro & Hotkey Globali | Permette di catturare eventi tastiera e mouse a livello di sistema operativo per il registratore di macro e ascoltare hotkey globali (es. F6, F7, F9, F10) anche quando l'applicazione è in background o in gioco. |
| **ctypes (Win32 API)** | Rimappatura & Iniezione Input | Utilizza `user32.dll` (`SendInput`, `SetWindowsHookExW` con `WH_MOUSE_LL`). Consente di intercettare fisicamente i pulsanti del mouse con soppressione dell'evento originale a latenza zero (< 1 ms), eliminando i ritardi delle librerie ad alto livello. |

### Comandi di Installazione

Assicurati di avere Python 3.10+ installato su Windows 11. Apri il terminale PowerShell ed esegui:

```powershell
pip install -r requirements.txt
```

oppure installale direttamente:

```powershell
pip install PySide6 hidapi pynput
```

---

## 🔬 Protocollo Hardware Razer Viper V3 HyperSpeed

Il mouse comunica tramite il dongle USB HyperSpeed 2.4 GHz identificato come:
- **Vendor ID (VID)**: `0x1532` (Razer Inc.)
- **Product ID (PID)**: `0x00B8` (Razer Viper V3 HyperSpeed)

### Struttura del Pacchetto Feature Report (90 Byte)
Ogni pacchetto inviato e ricevuto tramite `hid_send_feature_report` / `hid_get_feature_report` (con Report ID `0x00` anteposto, per 91 byte totali) rispetta il layout hardware documentato dalla community OpenRazer:

1. **Byte 0**: `Status` (`0x00` in invio, `0x02` in risposta indica operazione eseguita con successo).
2. **Byte 1**: `Transaction ID` (`0x1F`).
3. **Byte 2-3**: `Remaining Packets` (`0x00, 0x00` Big Endian).
4. **Byte 4**: `Protocol Type` (`0x00`).
5. **Byte 5**: `Data Size` (lunghezza degli argomenti validi).
6. **Byte 6**: `Command Class` (categoria del comando).
7. **Byte 7**: `Command ID` (istruzione specifica).
8. **Byte 8-87**: `Arguments` (fino a 80 byte di payload).
9. **Byte 88**: `CRC Checksum` (calcolato come XOR bit a bit dal byte 2 al byte 87 inclusi).
10. **Byte 89**: Byte di riserva (`0x00`).

### Funzioni Hardware supportate:
- **Lettura Livello Batteria**: `Class = 0x07`, `Command = 0x80`. Il byte di risposta in `args[1]` riporta il valore di carica da `0` a `255`, convertito in percentuale: `round(val / 255.0 * 100)`.
- **Stato di Ricarica**: `Class = 0x07`, `Command = 0x84`. Ritorna `1` se in carica via cavo, `0` se a batteria.
- **Lettura DPI**: `Class = 0x04`, `Command = 0x85`. Restituisce gli assi X e Y su due byte ciascuno `(hi << 8) | lo`.
- **Scrittura DPI**: `Class = 0x04`, `Command = 0x05`. Invia gli assi X e Y per impostare la sensibilità hardware del sensore ottico (fino a 30.000 DPI).
- **Lettura Polling Rate**: `Class = 0x00`, `Command = 0x85`. Restituisce il divisore hardware (`0x01` = 1000 Hz, `0x02` = 500 Hz, `0x04` = 250 Hz, `0x08` = 125 Hz).
- **Scrittura Polling Rate**: `Class = 0x00`, `Command = 0x05`. Applica istantaneamente il tasso di polling sul transceiver USB.

---

## ⚡ Distinzione: Funzioni Hardware vs Funzioni Software

È fondamentale chiarire come operano le varie funzionalità per trasparenza tecnica:

| Funzionalità | Livello di Esecuzione | Dettagli di Implementazione |
| :--- | :--- | :--- |
| **DPI (Sensibilità)** | **Hardware** (Sensore Ottico) | Inviato direttamente ai registri del sensore Razer Focus Pro 30K. Non altera la scala Windows, garantendo precisione 1:1 grezza. |
| **Polling Rate** | **Hardware** (Transceiver USB) | Negoziato via hardware sul bus USB a 1000 Hz, 500 Hz, 250 Hz o 125 Hz. |
| **Batteria & Ricarica** | **Hardware** (Chipset Interno) | Interrogazione dello stato di tensione e circuito di carica del mouse. |
| **Rimappatura Tasti** | **Software** (Hook Win32 OS) | Poiché il mouse Viper V3 HyperSpeed non supporta la memorizzazione onboard di sequenze tastiera arbitrarie senza driver, l'applicazione usa un hook `WH_MOUSE_LL` per intercettare i click nativi prima del sistema operativo, sopprimerli e generare l'input desiderato. |
| **Rapid-Fire** | **Software** (Thread ad alta precisione) | Genera un treno di click sintetici SendInput ogni *N* millisecondi mentre il tasto fisico è premuto. |
| **Macro & Autoclicker** | **Software** (Thread background) | Registra e riproduce eventi temporizzati con clock ad alta risoluzione (`perf_counter`). |

---

## 🚀 Istruzioni per l'Avvio

1. Posizionati nella directory dell'applicazione:
   ```powershell
   cd C:\Users\gigac\.gemini\antigravity-ide\scratch\razer_controller
   ```
2. Assicurati che il dongle USB Razer HyperSpeed sia inserito nel computer.
3. Avvia l'applicazione con il comando:
   ```powershell
   python main.py
   ```
   *(oppure con il percorso completo di Python se non in PATH)*:
   ```powershell
   & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" main.py
   ```

---

## ⌨️ Tasti Rapidi Globali Predefiniti

Tutte le scorciatoie funzionano anche quando l'app è minimizzata o durante una sessione di gioco a schermo intero:
- **`F6`**: Attiva / Disattiva l'Autoclicker.
- **`F7`**: Passa ciclicamente al profilo successivo (es. da "Gaming" a "Lavoro").
- **`F9`**: Inizia / Arresta la registrazione di una macro.
- **`F10`**: Avvia / Interrompe la riproduzione della macro attiva.

---

## ⚠️ Limiti Noti e Risoluzione Errori

1. **Razer Synapse in Esecuzione**:
   - Se il software proprietario Razer Synapse 3 o 4 è in esecuzione in background con i suoi servizi di telemetria, potrebbe bloccare l'interfaccia USB HID con accesso esclusivo.
   - *Soluzione*: Chiudi Razer Synapse dalla barra delle applicazioni per consentire all'applicazione di comunicare direttamente con l'hardware via HID.
2. **Permessi di Amministrazione su Giochi con Anti-Cheat (EAC / BattlEye / Vanguard)**:
   - Alcuni giochi competitivi con driver anti-cheat a livello kernel bloccano gli eventi sintetici di `SendInput` generati da processi a priorità normale o gli hook `WH_MOUSE_LL`.
   - *Soluzione*: Esegui l'applicazione con **"Esegui come Amministratore"** (tasto destro sul prompt o PowerShell) per dare al processo la medesima priorità del gioco.
3. **Consumo Batteria con Polling Rate a 1000 Hz**:
   - La frequenza di aggiornamento a 1000 Hz garantisce la massima reattività (1 ms), ma consuma la batteria AA del Viper V3 circa 3 volte più rapidamente rispetto a 500 Hz o 250 Hz.
4. **Modalità Sleep del Mouse**:
   - Quando il mouse entra in standby per inattività, il controller wireless potrebbe non rispondere immediatamente alla richiesta di batteria fino al primo movimento che risveglia il sensore.
