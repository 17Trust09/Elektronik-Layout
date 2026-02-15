from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from models.schema import (
    Circuit,
    ConfidenceType,
    Device,
    DeviceType,
    Endpoint,
    EndpointType,
    Panel,
    ProjectMeta,
    ProtectionLink,
    PurposeType,
    Room,
)
from services.database import Database

LOGGER = logging.getLogger(__name__)


class ProjectFS:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.db_path = self.root_dir / "project.db"
        self.attachments_dir = self.root_dir / "attachments"
        self.logs_dir = self.root_dir / "logs"

    def ensure(self) -> Database:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.attachments_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        db = Database(self.db_path)
        db.create_all()
        with db.session() as session:
            if session.query(ProjectMeta).count() == 0:
                LOGGER.info("Seeding demo data")
                self.seed_demo(session)
        return db

    def seed_demo(self, session: Session) -> None:
        session.add(ProjectMeta(name="Demo Haus", address="Musterstraße 1", notes="Automatisch erzeugt"))
        panel = Panel(name="UV EG", location="Erdgeschoss")
        session.add(panel)
        session.flush()

        rcds: list[Device] = []
        mcbs: list[Device] = []
        for i in range(2):
            rcd = Device(panel_id=panel.id, type=DeviceType.RCD, label=f"FI {i + 1}", rating="40A/30mA", poles=4, row=0, col=i)
            session.add(rcd)
            rcds.append(rcd)

        for i in range(10):
            mcb = Device(panel_id=panel.id, type=DeviceType.MCB, label=f"LS {i + 1}", rating="B16", poles=1, row=1 + i // 5, col=i % 5)
            session.add(mcb)
            mcbs.append(mcb)

        session.flush()
        rooms = [Room(name=n) for n in ["Flur", "Küche", "Wohnzimmer", "Bad", "Schlafzimmer", "Kinderzimmer", "Garage", "Garten"]]
        session.add_all(rooms)
        session.flush()

        circuits: list[Circuit] = []
        for i, mcb in enumerate(mcbs[:6]):
            c = Circuit(
                mcb_device_id=mcb.id,
                name=f"Stromkreis {i + 1}",
                purpose=PurposeType.SOCKETS if i % 2 == 0 else PurposeType.LIGHTS,
                confidence=ConfidenceType.UNKNOWN,
            )
            session.add(c)
            circuits.append(c)

        session.flush()
        endpoint_counter = 0
        for idx, c in enumerate(circuits):
            count = 5 if idx == 0 else 4  # ergibt exakt 25 Endpoints
            for j in range(count):
                room = rooms[(idx + j) % len(rooms)]
                endpoint_counter += 1
                session.add(
                    Endpoint(
                        circuit_id=c.id,
                        room_id=room.id,
                        type=EndpointType.SOCKET if j % 2 == 0 else EndpointType.LIGHT,
                        description=f"Endpoint {endpoint_counter}",
                        confidence=ConfidenceType.UNKNOWN,
                    )
                )

        for i, mcb in enumerate(mcbs):
            session.add(ProtectionLink(rcd_device_id=rcds[0].id if i < 5 else rcds[1].id, mcb_device_id=mcb.id))
