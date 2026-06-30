#!/usr/bin/env python3
"""
Pylontech BMS 6-Pack Live Dashboard - Version 2.4 (Chart-Separator Edition)
Optimiert mit vertikalen Trennlinien im Balkendiagramm nach je 15 Zellen,
globalen Radar-Highlights für Min/Max, 100% Breite und 6x15 Matrix.
"""

import socket
import time
import json
import threading
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ─────────────────────────────────────────────
# KONFIGURATION (Bitte an deine Anlage anpassen)
# ─────────────────────────────────────────────
BMS_HOST      = "192.168.178.xxx"   # Die IP-Adresse deines USR-TCP232 / RS485-zu-IP Konverters
BMS_PORT      = 8888              # Standard-Port des Konverters
BMS_TIMEOUT   = 10
POLL_INTERVAL = 60  
WEB_PORT      = 8081              # Port, unter dem das Dashboard im Browser erreichbar ist
NUM_PACKS     = 6                 # Anzahl deiner Pylontech-Module (z.B. 6 für 6-Pack)
# ─────────────────────────────────────────────

latest_data = {
    "cells": [],
    "pack": {},
    "history": [],
    "last_update": None,
    "error": None,
}
data_lock = threading.Lock()
HISTORY_FILE = "/var/log/pylontech_history_v2.json"

def save_history():
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(latest_data["history"], f)
    except:
        pass

def load_history():
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

latest_data["history"] = load_history()

def parse_bat(lines, pack_id):
    cells = []
    for line in lines:
        line = line.strip()
        m = re.match(r'^(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\d+)%\s+([\d]+)\s+mAH\s+(\w+)', line)
        if m:
            cell_num = int(m.group(1)) + 1
            cells.append({
                "pack":       pack_id,
                "cell":       cell_num,
                "label":      f"{pack_id}-{cell_num}",
                "voltage_mv": int(m.group(2)),
                "current_ma": int(m.group(3)),
                "temp_mc":    int(m.group(4)),
                "state":      m.group(5),
                "soc":        int(m.group(9)),
                "coulomb_mah": int(m.group(10)),
                "bal":        m.group(11) == "Y",
            })
    return cells

def parse_pwr(lines):
    data = {}
    for line in lines:
        line = line.strip()
        if ":" in line and not line[0].isdigit():
            key, _, val = line.partition(":")
            key = key.strip().lower().replace(" ", "_")
            val = val.strip().split()[0] if val.strip() else ""
            data[key] = val
    for line in lines:
        line = line.strip()
        parts = line.split()
        if len(parts) > 12 and parts[0].isdigit() and parts[1].isdigit():
            data["voltage"] = parts[1]
            data["current"] = parts[2]
            data["coulomb"] = parts[12].replace("%","")
            break
    return data

def poll_loop():
    while True:
        try:
            all_cells = []
            final_pwr = {}
            total_current_ma = 0
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Starte Abfrage-Zyklus...")
            
            with socket.create_connection((BMS_HOST, BMS_PORT), timeout=BMS_TIMEOUT) as s:
                time.sleep(1)
                
                for pack_id in range(1, NUM_PACKS + 1):
                    s.sendall(f"unit {pack_id}\r\n".encode("ascii"))
                    time.sleep(0.5)
                    
                    s.settimeout(0.3)
                    while True:
                        try:
                            if not s.recv(4096): break
                        except socket.timeout:
                            break
                    
                    s.sendall(b"bat\r\n")
                    time.sleep(1.2)
                    buf_bat = b""
                    s.settimeout(0.8)
                    while True:
                        try:
                            chunk = s.recv(4096)
                            if not chunk: break
                            buf_bat += chunk
                        except socket.timeout:
                            break
                    
                    bat_lines = buf_bat.decode("ascii", errors="ignore").replace("\r\r\n", "\n").replace("\r\n", "\n").splitlines()
                    pack_cells = parse_bat(bat_lines, pack_id)
                    all_cells.extend(pack_cells)
                    
                    s.sendall(b"pwr\r\n")
                    time.sleep(1.2)
                    buf_pwr = b""
                    s.settimeout(0.8)
                    while True:
                        try:
                            chunk = s.recv(4096)
                            if not chunk: break
                            buf_pwr += chunk
                        except socket.timeout:
                            break
                    
                    pwr_lines = buf_pwr.decode("ascii", errors="ignore").replace("\r\r\n", "\n").replace("\r\n", "\n").splitlines()
                    pack_pwr = parse_pwr(pwr_lines)
                    
                    if "current" in pack_pwr:
                        try:
                            total_current_ma += int(pack_pwr["current"])
                        except:
                            pass
                    
                    if pack_id == 1 or not final_pwr:
                        final_pwr.update(pack_pwr)
            
            if all_cells:
                final_pwr["total_current"] = total_current_ma
                now = datetime.now().strftime("%H:%M:%S")
                voltages = [c["voltage_mv"] for c in all_cells]
                snapshot = {
                    "time":   now,
                    "min":    min(voltages),
                    "max":    max(voltages),
                    "avg":    round(sum(voltages) / len(voltages)),
                    "spread": max(voltages) - min(voltages),
                    "cells":  voltages,
                }
                with data_lock:
                    latest_data["cells"]       = all_cells
                    latest_data["pack"]        = final_pwr
                    latest_data["last_update"] = now
                    latest_data["error"]       = None
                    latest_data["history"].append(snapshot)
                    if len(latest_data["history"]) > 7200:
                        latest_data["history"].pop(0)

                print(f" -> Erfolgreich! {len(all_cells)} Zellen erfasst.")
                if len(latest_data["history"]) % 5 == 0:
                    save_history()
            else:
                with data_lock:
                    latest_data["error"] = "Keine Zellen empfangen"

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Fehler im Multi-Poll-Loop: {e}")
            with data_lock:
                latest_data["error"] = str(e)

        time.sleep(POLL_INTERVAL)


HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pylontech 6-Pack Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0f1117; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; padding: 20px; width: 100%; }
  
  .header-container { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; flex-wrap: wrap; gap: 15px; width: 100%; }
  h1 { color: #4fc3f7; font-size: 1.4em; }
  
  .filter-buttons { display: flex; gap: 6px; flex-wrap: wrap; }
  .btn { color: #e0e0e0; border: 1px solid #3a3f54; padding: 6px 14px; border-radius: 6px; font-size: 0.85em; cursor: pointer; transition: all 0.2s; font-weight: 500; }
  .btn.btn-all { background: #1a1d27; }
  .btn.pack-odd { background: #1e2230; }
  .btn.pack-even { background: #13151d; }
  .btn:hover { border-color: #4fc3f7; color: #4fc3f7; }
  .btn.active { background: #4fc3f7 !important; color: #0f1117 !important; border-color: #4fc3f7 !important; font-weight: bold; }
  
  .subtitle { color: #888; font-size: 0.85em; margin-bottom: 20px; }
  
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; margin-bottom: 20px; width: 100%; }
  .stat { background: #1a1d27; border-radius: 10px; padding: 12px 10px; text-align: center; }
  .stat .val { font-size: 1.4em; font-weight: bold; line-height: 1.2; }
  .stat .lbl { font-size: 0.72em; color: #888; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
  .stat .loc { font-size: 0.55em; color: #aaa; font-weight: normal; margin-top: 2px; display: block; text-transform: none; }
  
  .stat.min-cell .val { color: #a0aec0; } 
  .stat.warn .val { color: #ffb74d; }     
  .stat.ok .val   { color: #81c784; }
  .stat.info .val { color: #4fc3f7; }
  .stat.err .val  { color: #e57373; }
  
  .cells { display: grid; grid-template-columns: repeat(15, 1fr); gap: 6px; margin-bottom: 20px; width: 100%; }
  .cell { border-radius: 6px; padding: 6px 4px; text-align: center; border: 2px solid transparent; transition: background 0.3s; }
  
  .cell.pack-odd  { background: #1e2230; }
  .cell.pack-even { background: #13151d; }
  
  .cell.balancing { border-color: #4fc3f7; }
  
  .cell.global-min { border-color: #a0aec0 !important; background: #2d323f !important; } 
  .cell.global-max { border-color: #ffb74d !important; background: #3e2e13 !important; } 
  
  .cell.low  { border-color: #4fc3f7; background: #0d1f2a !important; }
  .cell.high { border-color: #ffb74d; background: #2a1e00 !important; }
  .cell.danger { border-color: #e57373; background: #2a1010 !important; }
  
  .cell .cv { font-size: 1.05em; font-weight: bold; }
  .cell .ci { font-size: 0.68em; color: #aaa; margin-bottom: 2px; font-weight: 600; }
  .cell .cb { font-size: 0.65em; color: #4fc3f7; margin-top: 2px; height: 12px; }
  .cell .cs { font-size: 0.62em; color: #888; }
  
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; width: 100%; }
  .card { background: #1a1d27; border-radius: 10px; padding: 16px; }
  .card h2 { font-size: 0.9em; color: #aaa; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }
  canvas { width: 100% !important; }
  .error { background: #2a1a1a; border: 1px solid #e57373; border-radius: 8px; padding: 12px; color: #e57373; margin-bottom: 16px; }
  .update { color: #555; font-size: 0.75em; margin-top: 16px; text-align: right; }
</style>
</head>
<body>

<div class="header-container">
  <h1>⚡ Pylontech Multi-Pack Dashboard</h1>
  <div class="filter-buttons" id="pack-filter-btns">
    <button class="btn btn-all active" onclick="setFilter('all')">📊 Alle 6 Packs</button>
    <button class="btn pack-odd" onclick="setFilter(1)">🔋 Pack 1</button>
    <button class="btn pack-even" onclick="setFilter(2)">🔋 Pack 2</button>
    <button class="btn pack-odd" onclick="setFilter(3)">🔋 Pack 3</button>
    <button class="btn pack-even" onclick="setFilter(4)">🔋 Pack 4</button>
    <button class="btn pack-odd" onclick="setFilter(5)">🔋 Pack 5</button>
    <button class="btn pack-even" onclick="setFilter(6)">🔋 Pack 6</button>
  </div>
</div>
<div class="subtitle">6x Pylontech US-Serie im Verbund (15-Zellen Matrix)</div>

<div id="error-box" class="error" style="display:none"></div>

<div class="stats">
  <div class="stat info"><div class="val" id="s-voltage">–</div><div class="lbl">System-Spannung</div></div>
  <div class="stat min-cell"><div class="val" id="s-min">–</div><div class="lbl">Min Zelle (Global)</div></div>
  <div class="stat warn"><div class="val" id="s-max">–</div><div class="lbl">Max Zelle (Global)</div></div>
  <div class="stat"      ><div class="val" id="s-spread">–</div><div class="lbl">System-Spread</div></div>
  <div class="stat info"><div class="val" id="s-soc">–</div><div class="lbl">Schnitt SOC</div></div>
  <div class="stat"      ><div class="val" id="s-bal">–</div><div class="lbl">Balancing</div></div>
  <div class="stat info"><div class="val" id="s-curr">–</div><div class="lbl">Master-Strom</div></div>
  <div class="stat info"><div class="val" id="s-curr-total">–</div><div class="lbl">Gesamt-Strom</div></div>
  <div class="stat info"><div class="val" id="s-temp">–</div><div class="lbl">Schnitt Temp</div></div>
</div>

<div class="cells" id="cells-grid"></div>

<div class="grid">
  <div class="card">
    <h2>Zellspannungen (Gefiltert)</h2>
    <canvas id="chart-bar"></canvas>
  </div>
  <div class="card">
    <h2>Gesamtsystem-Verlauf (Global)</h2>
    <canvas id="chart-spread"></canvas>
  </div>
</div>

<div class="update" id="last-update">–</div>

<script>
let barChart, spreadChart;
let globalData = null;
let currentFilter = 'all';

function setFilter(val) {
  currentFilter = val;
  const btns = document.querySelectorAll('#pack-filter-btns .btn');
  btns.forEach(btn => btn.classList.remove('active'));
  if (val === 'all') {
    btns[0].classList.add('active');
  } else {
    btns[val].classList.add('active');
  }
  updateDashboard();
}

function initCharts() {
  const barCtx = document.getElementById('chart-bar').getContext('2d');
  barChart = new Chart(barCtx, {
    type: 'bar',
    data: { labels: [], datasets: [{ label: 'mV', data: [], backgroundColor: [], borderRadius: 4 }] },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { min: 3200, max: 3650, grid: { color: '#2a2d3a' }, ticks: { color: '#888' } },
        x: { grid: { display: false }, ticks: { color: '#888', font: { size: 9 } } }
      }
    },
    // NEU: Plugin für die vertikalen Trennlinien alle 15 Zellen
    plugins: [{
      id: 'packSeparator',
      afterDatasetsDraw(chart) {
        const { ctx, chartArea: { top, bottom }, scales: { x } } = chart;
        const dataLength = chart.data.labels.length;
        
        // Wenn gefiltert ist und nur 15 Zellen sichtbar sind, brauchen wir keine Trennlinie
        if (dataLength <= 15) return;
        
        ctx.save();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.22)'; // Dezent hellgraue Linie
        ctx.lineWidth = 1.5;
        ctx.setLineDash([5, 4]); // Schön gestrichelt
        
        // Loop zeichnet exakt im Zwischenraum zwischen Zelle 15 und 16 (Index 14 und 15) etc.
        for (let i = 14; i < dataLength - 1; i += 15) {
          const xPos = (x.getPixelForValue(i) + x.getPixelForValue(i + 1)) / 2;
          ctx.beginPath();
          ctx.moveTo(xPos, top);
          ctx.lineTo(xPos, bottom);
          ctx.stroke();
        }
        ctx.restore();
      }
    }]
  });

  const spreadCtx = document.getElementById('chart-spread').getContext('2d');
  spreadChart = new Chart(spreadCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        { label: 'Min mV',  data: [], borderColor: '#4fc3f7', backgroundColor: 'transparent', tension: 0.2, pointRadius: 0, borderWidth: 1.5 },
        { label: 'Avg mV',  data: [], borderColor: '#81c784', backgroundColor: 'transparent', tension: 0.2, pointRadius: 0, borderWidth: 1.5 },
        { label: 'Max mV',  data: [], borderColor: '#ffb74d', backgroundColor: 'transparent', tension: 0.2, pointRadius: 0, borderWidth: 1.5 },
      ]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: '#888', boxWidth: 12 } } },
      scales: {
        y:  { min: 3200, max: 3650, grid: { color: '#2a2d3a' }, ticks: { color: '#888' } },
        x:  { grid: { display: false }, ticks: { color: '#555', maxTicksLimit: 8 } }
      }
    }
  });
}

function cellColor(mv, avgMv) {
  if (mv >= 3550) return '#e57373';
  if (mv >= 3500) return '#ffb74d';
  if (mv < avgMv - 30) return '#4fc3f7';
  if (mv > avgMv + 30) return '#ffb74d';
  return '#81c784';
}

function updateDashboard() {
  if (!globalData) return;
  const filterValue = currentFilter;
  
  const err = document.getElementById('error-box');
  if (globalData.error) {
    err.style.display = 'block';
    err.textContent = 'Fehler: ' + globalData.error;
    return;
  }
  err.style.display = 'none';

  let cells = globalData.cells;
  if (!cells.length) return;

  let globalMinCell = cells[0];
  let globalMaxCell = cells[0];
  cells.forEach(c => {
    if (c.voltage_mv < globalMinCell.voltage_mv) globalMinCell = c;
    if (c.voltage_mv > globalMaxCell.voltage_mv) globalMaxCell = c;
  });

  const globalMin = globalMinCell.voltage_mv;
  const globalMax = globalMaxCell.voltage_mv;
  const globalSpread = globalMax - globalMin;
  const globalBalCount = cells.filter(c => c.bal).length;
  const globalAvgSoc = Math.round(cells.reduce((a,c) => a + c.soc, 0) / cells.length);

  document.getElementById('s-voltage').textContent = (globalData.pack.voltage ? (globalData.pack.voltage/1000).toFixed(2) + ' V' : '–');
  document.getElementById('s-min').innerHTML = `${globalMin} mV <span class="loc">Pack ${globalMinCell.pack}, Zelle ${globalMinCell.cell}</span>`;
  document.getElementById('s-max').innerHTML = `${globalMax} mV <span class="loc">Pack ${globalMaxCell.pack}, Zelle ${globalMaxCell.cell}</span>`;
  document.getElementById('s-spread').textContent = globalSpread + ' mV';
  document.getElementById('s-soc').textContent = globalAvgSoc + '%';
  document.getElementById('s-bal').textContent = globalBalCount > 0 ? globalBalCount + ' Z.' : 'Nein';
  
  const avgCurr = (globalData.pack.current ? (parseInt(globalData.pack.current)/1000).toFixed(1) : '–');
  document.getElementById('s-curr').textContent = avgCurr + ' A';
  
  const totalCurr = (globalData.pack.total_current ? (parseInt(globalData.pack.total_current)/1000).toFixed(1) : '–');
  document.getElementById('s-curr-total').textContent = totalCurr + ' A';
  
  const avgTemp = (cells.reduce((a,c) => a + c.temp_mc, 0) / cells.length / 1000).toFixed(1);
  document.getElementById('s-temp').textContent = avgTemp + ' °C';

  const spreadEl = document.getElementById('s-spread').parentElement;
  spreadEl.className = 'stat ' + (globalSpread > 100 ? 'err' : globalSpread > 40 ? 'warn' : 'ok');

  if (filterValue !== 'all') {
    const pId = parseInt(filterValue);
    cells = cells.filter(c => c.pack === pId);
  }

  const filteredVoltages = cells.map(c => c.voltage_mv);
  const filteredAvg = Math.round(filteredVoltages.reduce((a,b) => a+b, 0) / filteredVoltages.length);

  const grid = document.getElementById('cells-grid');
  grid.innerHTML = '';
  cells.forEach(c => {
    const isGlobalMin = (c.pack === globalMinCell.pack && c.cell === globalMinCell.cell);
    const isGlobalMax = (c.pack === globalMaxCell.pack && c.cell === globalMaxCell.cell);

    const isDanger = c.voltage_mv >= 3550;
    const isWarn = c.voltage_mv >= 3500 && !isDanger;
    const isLow = c.voltage_mv < filteredAvg - 30;
    const isHigh = c.voltage_mv > filteredAvg + 30 && !isWarn && !isDanger;
    
    const packBgClass = (c.pack % 2 === 0) ? 'pack-even' : 'pack-odd';
    
    let clsList = ['cell', packBgClass];
    if (c.bal) clsList.push('balancing');
    
    if (isGlobalMin) clsList.push('global-min');
    else if (isGlobalMax) clsList.push('global-max');
    else if (isDanger) clsList.push('danger');
    else if (isWarn || isHigh) clsList.push('high');
    else if (isLow) clsList.push('low');
    
    const cls = clsList.join(' ');
    
    let displayColor = cellColor(c.voltage_mv, filteredAvg);
    if (isGlobalMin) displayColor = '#a0aec0';
    if (isGlobalMax) displayColor = '#ffb74d';
    
    grid.innerHTML += `
      <div class="${cls}">
        <div class="ci">Zelle ${c.label}</div>
        <div class="cv" style="color:${displayColor}">${c.voltage_mv}</div>
        <div class="cs">${c.soc}% · ${(c.coulomb_mah/1000).toFixed(1)}Ah</div>
        <div class="cb">${c.bal ? '⚡ BAL' : ''}</div>
      </div>`;
  });

  barChart.data.labels = cells.map(c => 'Z ' + c.label);
  barChart.data.datasets[0].data = filteredVoltages;
  barChart.data.datasets[0].backgroundColor = cells.map(c => {
    if (c.pack === globalMinCell.pack && c.cell === globalMinCell.cell) return '#a0aec0';
    if (c.pack === globalMaxCell.pack && c.cell === globalMaxCell.cell) return '#ffb74d';
    return cellColor(c.voltage_mv, filteredAvg);
  });
  barChart.update('none');

  if (globalData.history && globalData.history.length) {
    spreadChart.data.labels = globalData.history.map(h => h.time);
    spreadChart.data.datasets[0].data = globalData.history.map(h => h.min);
    spreadChart.data.datasets[1].data = globalData.history.map(h => h.avg);
    spreadChart.data.datasets[2].data = globalData.history.map(h => h.max);
    spreadChart.update('none');
  }

  document.getElementById('last-update').textContent = 'Letzte Aktualisierung: ' + globalData.last_update;
}

function fetchData() {
  fetch('/data')
    .then(r => r.json())
    .then(d => {
      globalData = d;
      updateDashboard();
    })
    .catch(e => {
      document.getElementById('error-box').style.display = 'block';
      document.getElementById('error-box').textContent = 'Verbindungsfehler zum Webserver.';
    });
}

initCharts();
fetchData();
setInterval(fetchData, 15000);
</script>
</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            if self.path == "/data":
                with data_lock:
                    payload = json.dumps(latest_data).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(payload)
            else:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(HTML.encode())
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Webserver-Notiz: {e}")

if __name__ == "__main__":
    print(f"Pylontech Dashboard v2.4 (Separator) startet...")
    t = threading.Thread(target=poll_loop, daemon=True)
    t.start()

    server = HTTPServer(("0.0.0.0", WEB_PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
