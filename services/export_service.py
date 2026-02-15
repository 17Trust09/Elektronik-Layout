from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from models.schema import Circuit, Device, Endpoint, Panel, ProtectionLink, Room


class ExportService:
    def __init__(self, templates_dir: Path) -> None:
        self.env = Environment(loader=FileSystemLoader(templates_dir), autoescape=select_autoescape())

    def export_json(self, session: Session, output_path: Path) -> None:
        data = {
            "panels": [
                {"id": p.id, "name": p.name, "location": p.location}
                for p in session.query(Panel).all()
            ],
            "devices": [
                {
                    "id": d.id,
                    "panel_id": d.panel_id,
                    "type": d.type.value,
                    "label": d.label,
                    "rating": d.rating,
                    "row": d.row,
                    "col": d.col,
                }
                for d in session.query(Device).all()
            ],
        }
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def export_html(self, session: Session, output_path: Path, css_path: Path) -> None:
        template = self.env.get_template("report.html")
        panels = session.query(Panel).all()
        links = session.query(ProtectionLink).all()
        circuits = session.query(Circuit).all()
        rooms = session.query(Room).all()
        endpoints = session.query(Endpoint).all()
        html = template.render(
            panels=panels,
            links=links,
            circuits=circuits,
            rooms=rooms,
            endpoints=endpoints,
            css=css_path.read_text(encoding="utf-8"),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
