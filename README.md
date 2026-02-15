# StromkreisDoku (Elektronik-Layout)

Windows Desktop-App (PySide6) zur Dokumentation einer Haus-Elektrik mit PanelView und Flow-Graph.

## Voraussetzungen
- Python 3.12
- Windows 10/11

## Start (Development)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python -m app
```

Beim ersten Start wird im Arbeitsverzeichnis `demo_project/` erzeugt (`project.db`, `attachments/`, `logs/app.log`) und automatisch mit Demo-Daten gefüllt.

## MVP-Funktionen
- 3-Spalten-Hauptfenster (Navigation | Tabs | Inspector) + Statusbar.
- Tabs: `PanelView`, `GraphView`, `Rooms`.
- PanelView: Drag&Drop persistiert `row/col`, Kontextmenü (Add/Delete/Assign to RCD).
- GraphView: Layered Layout, Ctrl+Wheel Zoom, Filter `Nur Unknown/Likely`, Fit-Graph.
- RCD Mapping Wizard (persistente ProtectionLinks).
- Test Mode Wizard (LS-Off Verifikation setzt Endpoint-Confidence auf `CONFIRMED`).
- Export: HTML Report (`exports/report.html`) und JSON Snapshot (`project.json`) inkl. JSON-Import.

## Intuitive Bedienung (empfohlener Ablauf)
1. Im `PanelView` Gerätepositionen prüfen/ziehen und FI→LS Mapping über den Wizard pflegen.
2. Im `GraphView` mit Filter „Nur Unknown/Likely“ offene Punkte eingrenzen.
3. Über `Test Mode` einen Stromkreis verifizieren und Endpoints bestätigen.
4. Über `Export HTML` + `Open Report` den druckbaren Bericht erzeugen.

## Build (PyInstaller)
```bash
pip install pyinstaller
pyinstaller stromkreisdoku.spec
```

Die Spec bundelt Assets/Templates; Laufzeit-Pfade werden in `app/main.py` über `_MEIPASS` aufgelöst.
