from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView, QInputDialog, QMenu

from models.schema import Device, DeviceType, Panel


class DeviceItem(QGraphicsRectItem):
    def __init__(self, device: Device) -> None:
        super().__init__(0, 0, 120, 60)
        self.device_id = device.id
        self.setFlags(self.GraphicsItemFlag.ItemIsMovable | self.GraphicsItemFlag.ItemIsSelectable)
        self.setBrush(QBrush(QColor("#2d3748")))
        self.setPen(QPen(QColor("#718096"), 2))
        label = QGraphicsSimpleTextItem(f"{device.label}\n{device.rating}", self)
        label.setBrush(QBrush(QColor("#e2e8f0")))
        label.setPos(8, 8)


class PanelView(QGraphicsView):
    device_selected = Signal(int)
    assign_rcd_requested = Signal()

    def __init__(self, app_ctx) -> None:
        super().__init__()
        self.app_ctx = app_ctx
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.grid = 140

    def refresh(self) -> None:
        self.scene.clear()
        with self.app_ctx.db.session() as session:
            panel = session.query(Panel).first()
            if not panel:
                return
            devices = session.query(Device).filter(Device.panel_id == panel.id).all()
            for device in devices:
                item = DeviceItem(device)
                item.setPos(QPointF(device.col * self.grid, device.row * 80))
                self.scene.addItem(item)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        moved = [i for i in self.scene.selectedItems() if isinstance(i, DeviceItem)]
        if moved:
            with self.app_ctx.db.session() as session:
                for item in moved:
                    device = session.get(Device, item.device_id)
                    if device:
                        device.col = max(0, round(item.pos().x() / self.grid))
                        device.row = max(0, round(item.pos().y() / 80))
                self.app_ctx.data_changed.emit()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        item = self.itemAt(event.position().toPoint())
        if isinstance(item, DeviceItem):
            self.device_selected.emit(item.device_id)

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
            if not panel:
                return
            session.add(Device(panel_id=panel.id, type=DeviceType.OTHER, label=label, rating="", row=0, col=0))
        self.app_ctx.data_changed.emit()

    def _delete_selected_device(self) -> None:
        items = [i for i in self.scene.selectedItems() if isinstance(i, DeviceItem)]
        if not items:
            return
        with self.app_ctx.db.session() as session:
            for item in items:
                device = session.get(Device, item.device_id)
                if device:
                    session.delete(device)
        self.app_ctx.data_changed.emit()
