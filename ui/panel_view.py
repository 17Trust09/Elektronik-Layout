from __future__ import annotations

from PySide6.QtCore import QPointF, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView, QInputDialog, QMenu

from models.schema import Device, DeviceType, Panel, ProtectionLink


class DeviceItem(QGraphicsRectItem):
    def __init__(self, device: Device) -> None:
        super().__init__(0, 0, 140, 72)
        self.device_id = device.id
        self.device_type = device.type.value.lower()
        self.setFlags(self.GraphicsItemFlag.ItemIsMovable | self.GraphicsItemFlag.ItemIsSelectable)
        self.normal_pen = QPen(QColor("#718096"), 2)
        self.highlight_pen = QPen(QColor("#f6ad55"), 3)
        self.setBrush(QBrush(QColor("#2d3748")))
        self.setPen(self.normal_pen)
        text = f"{device.type.value}\n{device.label} ({device.rating})\nPos: {device.row}/{device.col}"
        label = QGraphicsSimpleTextItem(text, self)
        label.setBrush(QBrush(QColor("#e2e8f0")))
        label.setPos(8, 6)


class PanelView(QGraphicsView):
    entity_selected = Signal(str, int)
    assign_rcd_requested = Signal()

    def __init__(self, app_ctx) -> None:
        super().__init__()
        self.app_ctx = app_ctx
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.grid_x = 160
        self.grid_y = 90
        self._items: dict[int, DeviceItem] = {}

    def refresh(self) -> None:
        self.scene.clear()
        self._items.clear()
        with self.app_ctx.db.session() as session:
            panel = session.query(Panel).first()
            if not panel:
                return
            for device in session.query(Device).filter(Device.panel_id == panel.id).all():
                item = DeviceItem(device)
                item.setPos(QPointF(device.col * self.grid_x, device.row * self.grid_y))
                self.scene.addItem(item)
                self._items[device.id] = item

    def set_highlight(self, entity: str, entity_id: int) -> None:
        for item in self._items.values():
            item.setPen(item.normal_pen)

        with self.app_ctx.db.session() as session:
            if entity == "device":
                device = session.get(Device, entity_id)
                if not device:
                    return
                if entity_id in self._items:
                    self._items[entity_id].setPen(self._items[entity_id].highlight_pen)
                if device.type == DeviceType.RCD:
                    mcb_ids = [l.mcb_device_id for l in session.query(ProtectionLink).filter(ProtectionLink.rcd_device_id == entity_id).all()]
                    for mcb_id in mcb_ids:
                        if mcb_id in self._items:
                            self._items[mcb_id].setPen(self._items[mcb_id].highlight_pen)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        moved = [i for i in self.scene.selectedItems() if isinstance(i, DeviceItem)]
        if not moved:
            return
        with self.app_ctx.db.session() as session:
            for item in moved:
                device = session.get(Device, item.device_id)
                if device:
                    device.col = max(0, round(item.pos().x() / self.grid_x))
                    device.row = max(0, round(item.pos().y() / self.grid_y))
        self.app_ctx.data_changed.emit()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        item = self.itemAt(event.position().toPoint())
        if isinstance(item, DeviceItem):
            self.entity_selected.emit("device", item.device_id)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        add_action = QAction("Add Device", self)
        del_action = QAction("Delete Device", self)
        assign_action = QAction("Assign to RCD", self)
        menu.addAction(add_action)
        menu.addAction(del_action)
        menu.addAction(assign_action)
        choice = menu.exec(event.globalPos())
        if choice == add_action:
            self._add_device()
        elif choice == del_action:
            self._delete_selected_device()
        elif choice == assign_action:
            self.assign_rcd_requested.emit()

    def _add_device(self) -> None:
        label, ok = QInputDialog.getText(self, "Device", "Label")
        if not ok or not label:
            return
        with self.app_ctx.db.session() as session:
            panel = session.query(Panel).first()
            if panel is None:
                return
            session.add(Device(panel_id=panel.id, type=DeviceType.OTHER, label=label, rating="", row=0, col=0))
        self.app_ctx.data_changed.emit()

    def _delete_selected_device(self) -> None:
        selected = [i for i in self.scene.selectedItems() if isinstance(i, DeviceItem)]
        if not selected:
            return
        with self.app_ctx.db.session() as session:
            for item in selected:
                device = session.get(Device, item.device_id)
                if device:
                    session.delete(device)
        self.app_ctx.data_changed.emit()
