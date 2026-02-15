from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from models.schema import Circuit, Device, DeviceType, Endpoint, Panel, ProtectionLink, Room, PurposeType, ConfidenceType, EndpointType


class ExportService:
    def __init__(self, templates_dir: Path) -> None:
        self.env = Environment(loader=FileSystemLoader(templates_dir), autoescape=select_autoescape())

    def export_json(self, session: Session, output_path: Path) -> None:
        data = {
            "panels": [{"id": p.id, "name": p.name, "location": p.location} for p in session.query(Panel).all()],
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
            "links": [{"rcd_device_id": l.rcd_device_id, "mcb_device_id": l.mcb_device_id} for l in session.query(ProtectionLink).all()],
            "circuits": [
                {
                    "id": c.id,
                    "mcb_device_id": c.mcb_device_id,
                    "name": c.name,
                    "purpose": c.purpose.value,
                    "confidence": c.confidence.value,
                }
                for c in session.query(Circuit).all()
            ],
            "rooms": [{"id": r.id, "name": r.name, "floor": r.floor} for r in session.query(Room).all()],
            "endpoints": [
                {
                    "id": e.id,
                    "circuit_id": e.circuit_id,
                    "room_id": e.room_id,
                    "type": e.type.value,
                    "description": e.description,
                    "confidence": e.confidence.value,
                }
                for e in session.query(Endpoint).all()
            ],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def import_json(self, session: Session, input_path: Path) -> None:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        session.query(Endpoint).delete()
        session.query(Circuit).delete()
        session.query(ProtectionLink).delete()
        session.query(Device).delete()
        session.query(Room).delete()
        session.query(Panel).delete()

        for panel in payload.get("panels", []):
            session.add(Panel(id=panel["id"], name=panel["name"], location=panel.get("location", "")))
        for room in payload.get("rooms", []):
            session.add(Room(id=room["id"], name=room["name"], floor=room.get("floor", "")))
        for d in payload.get("devices", []):
            session.add(
                Device(
                    id=d["id"],
                    panel_id=d["panel_id"],
                    type=DeviceType(d["type"]),
                    label=d["label"],
                    rating=d.get("rating", ""),
                    row=d.get("row", 0),
                    col=d.get("col", 0),
                    poles=1,
                )
            )
        for l in payload.get("links", []):
            session.add(ProtectionLink(rcd_device_id=l["rcd_device_id"], mcb_device_id=l["mcb_device_id"]))
        for c in payload.get("circuits", []):
            session.add(
                Circuit(
                    id=c["id"],
                    mcb_device_id=c["mcb_device_id"],
                    name=c["name"],
                    purpose=PurposeType(c.get("purpose", "OTHER")),
                    confidence=ConfidenceType(c.get("confidence", "UNKNOWN")),
                )
            )
        for e in payload.get("endpoints", []):
            session.add(
                Endpoint(
                    id=e["id"],
                    circuit_id=e["circuit_id"],
                    room_id=e["room_id"],
                    type=EndpointType(e.get("type", "OTHER")),
                    description=e.get("description", ""),
                    confidence=ConfidenceType(e.get("confidence", "UNKNOWN")),
                )
            )

    def export_html(self, session: Session, output_path: Path, css_path: Path) -> None:
        template = self.env.get_template("report.html")
        panels = session.query(Panel).all()
        links = session.query(ProtectionLink).all()
        circuits = session.query(Circuit).all()
        endpoints = session.query(Endpoint).all()
        devices = {d.id: d for d in session.query(Device).all()}
        rooms = {r.id: r for r in session.query(Room).all()}

        html = template.render(
            panels=panels,
            links=links,
            circuits=circuits,
            endpoints=endpoints,
            devices=devices,
            rooms=rooms,
            css=css_path.read_text(encoding="utf-8"),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
