# Pylontech BMS 6-Pack Live Dashboard

Live HTML Dashboard für 6x Pylontech US-Serie Akkus über RS485-zu-IP Konverter.
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

## System-Architektur & Hintergrund-Setup

Damit das Dashboard dauerhaft stabil läuft, ist das System in drei Komponenten aufgeteilt:

### 1. ser2net (Seriell-zu-Netzwerk Gateway)
Ein Standard-Linux-Tool, das den seriellen USB-Port (der am Pylontech-Konsolenport hängt) im lokalen Netzwerk freigibt.
- **Pfad:** `/usr/sbin/ser2net`
- **Konfiguration:** `/etc/ser2net.yaml`
- **Aufgabe:** Macht den USB-Port auf Netzwerk-Port `8888` erreichbar, damit das Python-Skript darauf zugreifen kann.

### 2. Das Dashboard-Skript
- **Pfad:** `/usr/local/bin/pylontech_dashboard.py`
- **Aufgabe:** Verbindet sich mit Port `8888` (ser2net), sendet die Befehle `bat` und `pwr` an das BMS, parst die Antworten und stellt den Webserver auf Port `8081` bereit. Die Webseite aktualisiert sich alle 15 Sekunden automatisch.

### 3. Autostart via systemd (Linux-Dienste)
Zwei Hintergrund-Dienste sorgen dafür, dass beide Programme nach einem Stromausfall oder Neustart des Servers automatisch im Hintergrund starten:
- `/etc/systemd/system/ser2net.service` (für das USB-Netzwerk-Gateway)
- `/etc/systemd/system/pylontech-dashboard.service` (für das Python-Skript)

_____________________________________________________________________

## 🕶️ Über dieses Projekt (Beichte eines Vibe-Coders)

Eine wichtige Sache vorweg: Ich bin kein gelernter Software-Entwickler und habe ehrlicherweise keine tiefere Ahnung von den wilden Regex-Ausdrücken, dem asynchronen Socket-Handling oder den Tiefen der Python-Netzwerkprogrammierung in diesem Skript. 

Ich bin ein stolzer **Vibe-Coder**! 😎

Ich hatte die Vision für das perfekte, übersichtliche Pylontech-Dashboard, die Hardware im Keller und eine KI als unermüdlichen Co-Piloten an meiner Seite. Gemeinsam haben wir geschwitzt, geflucht und dieses Tool gebaut. Es ist aus einer Notwendigkeit entstanden, um die Packs auszubalancieren und dabei die Ladeströme und Spannungen im Auge zu behalten. Mission geglückt. Die Packs laufen jetzt absolut perfekt und das Dashboard ist nice to have.

- **Wenn du hochoffiziellen, akademisch perfekten Senior-Entwickler-Code suchst:** Bist du hier eventuell falsch.
- **Wenn du ein Dashboard suchst, das verdammt noch mal einfach funktioniert, deine Zellen schützt und im Keller mega aussieht:** Willkommen im Club! Feel the vibe und lass gerne einen Stern⭐ da.
