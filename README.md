# pylontech-bms-dashboard
Live HTML Dashboard für 6x Pylontech US-Serie Akkus über RS485-zu-IP Konverter

# Pylontech BMS 6-Pack Live Dashboard

Ein schlankes, performantes Python-Skript, das die Zelldaten von bis zu 6 parallel geschalteten Pylontech LiFePO4-Akkus (US-Serie) ausliest und als interaktives HTML-Dashboard im lokalen Netzwerk bereitstellt.

## Features
- **6x15 Matrix:** Visualisierung aller 90 Einzelzellen auf einen Blick.
- **Top-Balancing Ansicht:** Automatische optische Hervorhebung von balancierenden Zellen (`⚡ BAL`).
- **Globaler Radar:** Automatische Erkennung der absolut niedrigsten und höchsten Zellspannung im gesamten Verbund.
- **Verlaufsdiagramm:** Anzeige von Min/Max/Schnitt-Spannungen über die Zeit.
- **Sicher & Lokal:** Keine Cloud, keine Passwörter, reine lokale Socket-Abfrage.

## Voraussetzungen
- Ein RS485-zu-IP Konverter (z. B. USR-TCP232-304), der an den Konsolen-Port des Master-Pylontech-Akkus angeschlossen ist.
- Python 3.x installiert auf einem dauerhaft laufenden Gerät (z. B. Raspberry Pi, Mini-PC, o.ä.).

## Installation & Start
1. Kopiere die Datei `dashboard.py` auf dein Gerät.
2. Öffne die Datei und trage oben deine `BMS_HOST` (IP-Adresse deines Konverters) ein.
3. Starte das Skript im Terminal:
   ```bash
   python3 dashboard.py

<img width="2174" height="1321" alt="Bildschirmfoto 2026-06-30 um 16 31 24" src="https://github.com/user-attachments/assets/1c920e4c-ff24-4163-91db-201fbb12c9db" />
<img width="2172" height="912" alt="Bildschirmfoto 2026-06-30 um 16 34 02" src="https://github.com/user-attachments/assets/fd982c8b-3f48-4954-b571-750d5f7cca84" />

