from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView

from models.schema import Circuit, Device, DeviceType, Endpoint, ProtectionLink, Room
from services.graph_layout import LayoutNode, layered_positions


class NodeItem(QGraphicsEllipseItem):
    def __init__(self, key: str, title: str) -> None:
        super().__init__(0, 0, 130, 56)
        self.key = key
        self.setBrush(QBrush(QColor("#1a202c")))
        self.setPen(QPen(QColor("#63b3ed"), 1.5))
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)
        text = QGraphicsSimpleTextItem(title, self)
        text.setBrush(QBrush(QColor("#edf2f7")))
        text.setPos(8, 20)


class GraphView(QGraphicsView):
    node_selected = Signal(str, int)

    def __init__(self, app_ctx) -> None:
        super().__init__()
        self.app_ctx = app_ctx
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.2 if event.angleDelta().y() > 0 else 0.8
            self.scale(factor, factor)
            return
        super().wheelEvent(event)

    def refresh(self) -> None:
        self.scene.clear()
        nodes: list[LayoutNode] = []
        titles: dict[str, str] = {}
        edges: list[tuple[str, str]] = []

        with self.app_ctx.db.session() as session:
            rcd_by_id = {d.id: d for d in session.query(Device).filter(Device.type == DeviceType.RCD).all()}
            mcb_by_id = {d.id: d for d in session.query(Device).filter(Device.type == DeviceType.MCB).all()}
            circuits = {c.id: c for c in session.query(Circuit).all()}
            rooms = {r.id: r for r in session.query(Room).all()}
            endpoints = session.query(Endpoint).all()
            links = session.query(ProtectionLink).all()

            for rcd in rcd_by_id.values():
                key = f"device:{rcd.id}"
                nodes.append(LayoutNode(key=key, layer=0, index=0))
                titles[key] = rcd.label

            for mcb in mcb_by_id.values():
                key = f"device:{mcb.id}"
                nodes.append(LayoutNode(key=key, layer=1, index=0))
                titles[key] = mcb.label

            for c in circuits.values():
                key = f"circuit:{c.id}"
                nodes.append(LayoutNode(key=key, layer=2, index=0))
                titles[key] = c.name

            for r in rooms.values():
                key = f"room:{r.id}"
                nodes.append(LayoutNode(key=key, layer=3, index=0))
                titles[key] = r.name

            for e in endpoints:
                key = f"endpoint:{e.id}"
                nodes.append(LayoutNode(key=key, layer=4, index=0))
                titles[key] = e.description or e.type.value

            for l in links:
                edges.append((f"device:{l.rcd_device_id}", f"device:{l.mcb_device_id}"))
            for c in circuits.values():
                edges.append((f"device:{c.mcb_device_id}", f"circuit:{c.id}"))
            for e in endpoints:
                edges.append((f"circuit:{e.circuit_id}", f"room:{e.room_id}"))
                edges.append((f"room:{e.room_id}", f"endpoint:{e.id}"))

        positions = layered_positions(nodes)
        node_items: dict[str, NodeItem] = {}
        for key, (x, y) in positions.items():
            item = NodeItem(key, titles.get(key, key))
            item.setPos(x, y)
            self.scene.addItem(item)
            node_items[key] = item

        for source, target in edges:
            if source in node_items and target in node_items:
                s = node_items[source].sceneBoundingRect().center()
                t = node_items[target].sceneBoundingRect().center()
                self.scene.addItem(QGraphicsLineItem(s.x(), s.y(), t.x(), t.y()))

        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        item = self.itemAt(event.position().toPoint())
        if isinstance(item, NodeItem):
            entity, id_str = item.key.split(":")
            self.node_selected.emit(entity, int(id_str))
