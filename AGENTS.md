# AGENTS.md — StromkreisDoku (Windows Desktop)

Du bist ein Senior Python Desktop Engineer. Ziel ist eine Windows Desktop-App zur Dokumentation einer Haus-Elektrik:
Zähler -> Hauptschalter/Hauptsicherung (optional) -> RCD/FI -> MCB/LS -> Circuit/Stromkreis -> Rooms -> Endpoints.

Kernanforderungen
- Windows-only. Python 3.12. PySide6 (Qt).
- Persistenz: SQLite via SQLAlchemy 2.x. Pro Projekt ein Ordner: project.db + attachments/.
- UI: modern, optisch ansprechend, konsistent (Dark Theme default, Light optional).
- Zentrale Visualisierung: Sicherungskasten (PanelView) + Flow Graph (GraphView), beide interaktiv.
- Keine “Fake UI”: alles muss klickbar sein und Daten speichern/laden.
- Keine unklaren Platzhalter: wenn etwas als Feature erwähnt wird, muss es im MVP funktionieren.

Code-Qualität
- Struktur sauber in Packages: app/, ui/, models/, services/, assets/.
- Type hints überall. Pydantic DTOs optional, aber nur wenn sinnvoll.
- Keine globalen Singletons außer sauberem App Context.
- SQLAlchemy Sessions: context-managed, thread-safe (UI Thread).
- Logging: Python logging, Level INFO, logfile im Projektordner (logs/app.log).
- Fehlerbehandlung: user-friendly QMessageBox + log details.

UI/UX Details
- Hauptfenster: 3-Spalten Layout:
  - Left: Navigation (Tree/Lists)
  - Center: Tabs: [PanelView | GraphView | Rooms]
  - Right: Inspector (Form Cards)
  - Bottom: Statusbar (Projektpfad, Filter, Selection, Dirty state)
- Dark Theme default: QSS in assets/theme_dark.qss. (Light optional)
- Icons: assets/icons/*.svg (minimal Set: meter, switch, rcd, mcb, circuit, room, socket, light, warning, photo)

Visualisierung
1) PanelView (Sicherungskasten)
- QGraphicsView/QGraphicsScene
- Panel als Raster (Rows/Cols). Geräte als “Modules” (rounded rect card).
- Device Card zeigt: Icon + label + rating + position.
- Drag&Drop repositioniert (row/col) + speichert in DB.
- Klick:
  - RCD selektieren => highlight alle zugeordneten MCBs (ProtectionLinks)
  - MCB selektieren => zeigt Circuit + highlight im GraphView
- Kontextmenü:
  - Add Device
  - Delete Device
  - Assign to RCD (Shortcut zum Wizard)

2) GraphView (Flow)
- QGraphicsView mit Nodes/Edges:
  RCD -> MCB -> Circuit -> Room -> Endpoint
- Auto-Layout (simple layered layout L->R) in services/graph_layout.py
- Interaktion: Zoom (Ctrl+Wheel), Pan (Middle mouse), Fit-to-view Button.
- Node Styles:
  - Selected: stärkerer Border
  - Confirmed/Likely/Unknown: kleine Badge oder Outline (nicht grell)
- Klick auf Node aktualisiert Inspector und Navigation Selection.
- Filter: “Nur Unknown/Likely”, “Nur ausgewählter RCD/MCB”.

Datenmodell (SQLAlchemy)
- ProjectMeta (1 row): name, address, notes, created_at, updated_at
- Panel: id, name, location, photo_path(optional)
- Device: id, panel_id, type(enum), label, rating, poles, row, col, notes
  type enum: METER, MAIN_SWITCH, RCD, MCB, SPD, OTHER
- ProtectionLink: id, rcd_device_id, mcb_device_id (unique pair)
- Circuit: id, mcb_device_id(unique), name, purpose(enum), cable(optional), confidence(enum), notes
  purpose enum: SOCKETS, LIGHTS, APPLIANCE, OUTDOOR, GARAGE, IT, OTHER
  confidence enum: CONFIRMED, LIKELY, UNKNOWN
- Room: id, name, floor(optional), notes
- Endpoint: id, circuit_id, room_id, type(enum), description, confidence(enum), notes
  endpoint type enum: SOCKET, LIGHT, JUNCTION, FIXED_LOAD, SWITCH, OTHER
- Attachment: id, endpoint_id(nullable), device_id(nullable), room_id(nullable), file_path, caption, created_at
  (Attachments liegen als Datei in attachments/; DB speichert relativen Pfad)

Wizards (müssen funktionieren)
- RCD Mapping Wizard:
  - Schritt 1: RCD wählen (Dropdown aller RCD Devices im Panel)
  - Schritt 2: Liste aller MCB Devices (Checkbox)
  - Speichern: ProtectionLinks upsert; Entfernen nicht mehr ausgewählter Links
- Test Mode Wizard (MVP light, aber real):
  - Wähle MCB/Circuit
  - Zeigt alle Endpoints (nach Rooms gruppiert) mit Toggle: ON/OFF/UNKNOWN
  - Speichert TestSession (optional table) ODER direkt Endpoint confidence + notes “verified on …”
  - Minimal: setze Endpoint confidence = CONFIRMED wenn OFF bestätigt bei LS-Off Test

Export
- JSON Snapshot Export/Import (project.json) inkl. relativer attachment paths.
- HTML Report (Jinja2) nach exports/report.html:
  - Panel summary (table)
  - RCD->MCB mapping
  - Circuits list
  - Per circuit: endpoints by room
  - Open issues: unknown/likely
  - Druckfreundliches CSS (A4)

Packaging
- PyInstaller Windows:
  - One-folder build empfohlen (Assets + templates mit bundlen).
  - README.md mit Build & Run Steps.

Demo Data (beim ersten Start)
- Erzeuge Demo Projekt “Demo Haus”:
  - 1 Panel “UV EG”
  - 2 RCD, 10 MCB
  - 6 Circuits, 8 Rooms, 25 Endpoints
  - ProtectionLinks gesetzt
- App startet direkt mit Demo, wenn keine project.db existiert.

Akzeptanzkriterien (MVP)
- App startet ohne Fehler.
- Demo Projekt wird angezeigt.
- PanelView zeigt Devices im Raster und Drag&Drop speichert Position (Neustart bleibt).
- GraphView zeigt Flow. Klick auf RCD/MCB/Endpoint selektiert und Inspector zeigt/editiert Daten.
- RCD Wizard setzt Mapping; Graph/Highlights aktualisieren sich.
- HTML Export erzeugt Datei und öffnet per “Open Report” Button.
