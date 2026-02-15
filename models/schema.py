from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DeviceType(str, Enum):
    METER = "METER"
    MAIN_SWITCH = "MAIN_SWITCH"
    RCD = "RCD"
    MCB = "MCB"
    SPD = "SPD"
    OTHER = "OTHER"


class PurposeType(str, Enum):
    SOCKETS = "SOCKETS"
    LIGHTS = "LIGHTS"
    APPLIANCE = "APPLIANCE"
    OUTDOOR = "OUTDOOR"
    GARAGE = "GARAGE"
    IT = "IT"
    OTHER = "OTHER"


class ConfidenceType(str, Enum):
    CONFIRMED = "CONFIRMED"
    LIKELY = "LIKELY"
    UNKNOWN = "UNKNOWN"


class EndpointType(str, Enum):
    SOCKET = "SOCKET"
    LIGHT = "LIGHT"
    JUNCTION = "JUNCTION"
    FIXED_LOAD = "FIXED_LOAD"
    SWITCH = "SWITCH"
    OTHER = "OTHER"


class ProjectMeta(Base):
    __tablename__ = "project_meta"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(255), default="Demo Haus")
    address: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Panel(Base):
    __tablename__ = "panel"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(255), default="")
    photo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    devices: Mapped[list[Device]] = relationship(back_populates="panel", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "device"

    id: Mapped[int] = mapped_column(primary_key=True)
    panel_id: Mapped[int] = mapped_column(ForeignKey("panel.id"))
    type: Mapped[DeviceType] = mapped_column(SAEnum(DeviceType))
    label: Mapped[str] = mapped_column(String(255))
    rating: Mapped[str] = mapped_column(String(64), default="")
    poles: Mapped[int] = mapped_column(default=1)
    row: Mapped[int] = mapped_column(default=0)
    col: Mapped[int] = mapped_column(default=0)
    notes: Mapped[str] = mapped_column(Text, default="")

    panel: Mapped[Panel] = relationship(back_populates="devices")
    circuit: Mapped[Circuit | None] = relationship(back_populates="mcb_device", uselist=False)


class ProtectionLink(Base):
    __tablename__ = "protection_link"
    __table_args__ = (UniqueConstraint("rcd_device_id", "mcb_device_id", name="uq_rcd_mcb"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rcd_device_id: Mapped[int] = mapped_column(ForeignKey("device.id"))
    mcb_device_id: Mapped[int] = mapped_column(ForeignKey("device.id"))


class Circuit(Base):
    __tablename__ = "circuit"

    id: Mapped[int] = mapped_column(primary_key=True)
    mcb_device_id: Mapped[int] = mapped_column(ForeignKey("device.id"), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    purpose: Mapped[PurposeType] = mapped_column(SAEnum(PurposeType), default=PurposeType.OTHER)
    cable: Mapped[str] = mapped_column(String(64), default="")
    confidence: Mapped[ConfidenceType] = mapped_column(SAEnum(ConfidenceType), default=ConfidenceType.UNKNOWN)
    notes: Mapped[str] = mapped_column(Text, default="")

    mcb_device: Mapped[Device] = relationship(back_populates="circuit")
    endpoints: Mapped[list[Endpoint]] = relationship(back_populates="circuit", cascade="all, delete-orphan")


class Room(Base):
    __tablename__ = "room"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    floor: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    endpoints: Mapped[list[Endpoint]] = relationship(back_populates="room")


class Endpoint(Base):
    __tablename__ = "endpoint"

    id: Mapped[int] = mapped_column(primary_key=True)
    circuit_id: Mapped[int] = mapped_column(ForeignKey("circuit.id"))
    room_id: Mapped[int] = mapped_column(ForeignKey("room.id"))
    type: Mapped[EndpointType] = mapped_column(SAEnum(EndpointType), default=EndpointType.OTHER)
    description: Mapped[str] = mapped_column(String(255), default="")
    confidence: Mapped[ConfidenceType] = mapped_column(SAEnum(ConfidenceType), default=ConfidenceType.UNKNOWN)
    notes: Mapped[str] = mapped_column(Text, default="")

    circuit: Mapped[Circuit] = relationship(back_populates="endpoints")
    room: Mapped[Room] = relationship(back_populates="endpoints")


class Attachment(Base):
    __tablename__ = "attachment"

    id: Mapped[int] = mapped_column(primary_key=True)
    endpoint_id: Mapped[int | None] = mapped_column(ForeignKey("endpoint.id"), nullable=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("device.id"), nullable=True)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("room.id"), nullable=True)
    file_path: Mapped[str] = mapped_column(String(255))
    caption: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def attachment_abs(project_dir: Path, rel_path: str) -> Path:
    return project_dir / rel_path
