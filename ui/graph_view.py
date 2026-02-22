from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView

from models.schema import Circuit, ConfidenceType, Device, DeviceType, Endpoint, ProtectionLink, Room
from services.graph_layout import LayoutNode, layered_positions


class NodeItem(QGraphicsEllipseItem):
    def __init__(self, key: str, title: str, confidence: ConfidenceType | None = None) -> None:
        super().__init__(0, 0, 140, 58)
        self.key = key
        self.normal_pen = QPen(QColor("#63b3ed"), 1.5)
        self.selected_pen = QPen(QColor("#f6ad55"), 3)
        if confidence == ConfidenceType.CONFIRMED:
            self.normal_pen = QPen(QColor("#68d391"), 1.8)
        elif confidence == ConfidenceType.LIKELY:
            self.normal_pen = QPen(QColor("#f6e05e"), 1.8)
        elif confidence == ConfidenceType.UNKNOWN:
            self.normal_pen = QPen(QColor("#a0aec0"), 1.8)
        self.setBrush(QBrush(QColor("#1a202c")))
        self.setPen(self.normal_pen)
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
        self.only_uncertain = False
        self.selected_device_filter: int | None = None
        self._node_items: dict[str, NodeItem] = {}

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.2 if event.angleDelta().y() > 0 else 0.8
            self.scale(factor, factor)
            return
        super().wheelEvent(event)

    def fit_graph(self) -> None:
        if not self.scene.items():
            return
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def set_filters(self, only_uncertain: bool, selected_device_id: int | None) -> None:
        self.only_uncertain = only_uncertain
        self.selected_device_filter = selected_device_id
        self.refresh()

    def set_highlight(self, entity: str, entity_id: int) -> None:
        for item in self._node_items.values():
            item.setPen(item.normal_pen)
        key = f"{entity}:{entity_id}"
        if key in self._node_items:
            self._node_items[key].setPen(self._node_items[key].selected_pen)

    def refresh(self) -> None:
        self.scene.clear()
        self._node_items.clear()
        nodes: list[LayoutNode] = []
        titles: dict[str, str] = {}
        confidences: dict[str, ConfidenceType | None] = {}
        edges: list[tuple[str, str]] = []

        with self.app_ctx.db.session() as session:
            rcd_by_id = {d.id: d for d in session.query(Device).filter(Device.type == DeviceType.RCD).all()}
            mcb_by_id = {d.id: d for d in session.query(Device).filter(Device.type == DeviceType.MCB).all()}
            circuits = {c.id: c for c in session.query(Circuit).all()}
            rooms = {r.id: r for r in session.query(Room).all()}
            endpoints = session.query(Endpoint).all()
            links = session.query(ProtectionLink).all()

            allowed_mcb_ids: set[int] | None = None
            if self.selected_device_filter:
                selected = session.get(Device, self.selected_device_filter)
                if selected and selected.type == DeviceType.RCD:
                    allowed_mcb_ids = {l.mcb_device_id for l in links if l.rcd_device_id == selected.id}
                elif selected and selected.type == DeviceType.MCB:
                    allowed_mcb_ids = {selected.id}

            def include_endpoint(ep: Endpoint) -> bool:
                if self.only_uncertain and ep.confidence == ConfidenceType.CONFIRMED:
                    return False
                if allowed_mcb_ids is not None:
                    circuit = circuits.get(ep.circuit_id)
                    if not circuit or circuit.mcb_device_id not in allowed_mcb_ids:
                        return False
                return True

            for rcd in rcd_by_id.values():
                key = f"device:{rcd.id}"
                nodes.append(LayoutNode(key=key, layer=0, index=0))
                titles[key] = rcd.label
                confidences[key] = None

            for mcb in mcb_by_id.values():
                if allowed_mcb_ids is not None and mcb.id not in allowed_mcb_ids:
                    continue
                key = f"device:{mcb.id}"
                nodes.append(LayoutNode(key=key, layer=1, index=0))
                titles[key] = mcb.label
                confidences[key] = None

            for c in circuits.values():
                if allowed_mcb_ids is not None and c.mcb_device_id not in allowed_mcb_ids:
                    continue
                key = f"circuit:{c.id}"
                nodes.append(LayoutNode(key=key, layer=2, index=0))
                titles[key] = c.name
                confidences[key] = c.confidence

            room_used: set[int] = set()
            for e in endpoints:
                if not include_endpoint(e):
                    continue
                room_used.add(e.room_id)

            for room_id in room_used:
                room = rooms[room_id]
                key = f"room:{room.id}"
                nodes.append(LayoutNode(key=key, layer=3, index=0))
                titles[key] = room.name
                confidences[key] = None

            for e in endpoints:
                if not include_endpoint(e):
                    continue
                key = f"endpoint:{e.id}"
                nodes.append(LayoutNode(key=key, layer=4, index=0))
                titles[key] = e.description or e.type.value
                confidences[key] = e.confidence

            for l in links:
                if allowed_mcb_ids is not None and l.mcb_device_id not in allowed_mcb_ids:
                    continue
                edges.append((f"device:{l.rcd_device_id}", f"device:{l.mcb_device_id}"))
            for c in circuits.values():
                if allowed_mcb_ids is not None and c.mcb_device_id not in allowed_mcb_ids:
                    continue
                edges.append((f"device:{c.mcb_device_id}", f"circuit:{c.id}"))
            for e in endpoints:
                if not include_endpoint(e):
                    continue
                edges.append((f"circuit:{e.circuit_id}", f"room:{e.room_id}"))
                edges.append((f"room:{e.room_id}", f"endpoint:{e.id}"))

        positions = layered_positions(nodes)
        for key, (x, y) in positions.items():
            item = NodeItem(key, titles.get(key, key), confidences.get(key))
            item.setPos(x, y)
            self.scene.addItem(item)
            self._node_items[key] = item

        for source, target in edges:
            if source in self._node_items and target in self._node_items:
                s = self._node_items[source].sceneBoundingRect().center()
                t = self._node_items[target].sceneBoundingRect().center()
                self.scene.addItem(QGraphicsLineItem(s.x(), s.y(), t.x(), t.y()))

        self.fit_graph()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        item = self.itemAt(event.position().toPoint())
        if isinstance(item, NodeItem):
            entity, id_str = item.key.split(":")
            self.node_selected.emit(entity, int(id_str))
