# StromkreisDoku (Elektronik-Layout)

Windows Desktop-App (PySide6) zur Dokumentation einer Haus-Elektrik inklusive Sicherungskasten- und Flow-Visualisierung.

## Voraussetzungen
- Python 3.12
- Windows 10/11

## Run (Dev)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python -m app
```

Beim ersten Start wird im aktuellen Verzeichnis automatisch `demo_project/` erstellt (`project.db`, `attachments/`, `logs/app.log`) und Demo-Daten geladen.

## Features (MVP)
- 3-Spalten-Hauptfenster mit Navigation, Tabs (PanelView/GraphView/Rooms), Inspector.
- SQLite Persistenz via SQLAlchemy.
- Interaktive PanelView mit Drag&Drop, Add/Delete und RCD-Zuordnung.
- GraphView mit Layer-Layout, Zoom (Ctrl+Wheel) und Selection-Sync.
- RCD Mapping Wizard.
- HTML-Export nach `demo_project/exports/report.html` + Open Report.

## Build (PyInstaller)
```bash
pip install pyinstaller
pyinstaller stromkreisdoku.spec
```

Assets/Templates werden über die Spec-Datei eingebunden. Laufzeitpfade werden in `app/main.py` über `_MEIPASS` aufgelöst.
