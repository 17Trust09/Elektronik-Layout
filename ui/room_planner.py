from __future__ import annotations

from collections import Counter

from PySide6.QtCore import QPointF, Signal
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QFormLayout,
    QGraphicsEllipseItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from models.schema import PlanItemType, Room, RoomPlanItem


class PlanMarker(QGraphicsEllipseItem):
    def __init__(self, item: RoomPlanItem, color: str) -> None:
        super().__init__(0, 0, 28, 28)
        self.plan_id = item.id
        self.setFlags(self.GraphicsItemFlag.ItemIsMovable | self.GraphicsItemFlag.ItemIsSelectable)
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(QColor("#f8fafc"), 1.4))
        text = QGraphicsSimpleTextItem(item.label, self)
        text.setBrush(QBrush(QColor("#e2e8f0")))
        text.setPos(34, 2)


class PlannerView(QGraphicsView):
    def __init__(self, planner_widget, scene):
        super().__init__(scene)
        self.planner_widget = planner_widget

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.planner_widget.persist_positions()
        self.planner_widget.changed.emit()


class RoomPlannerWidget(QWidget):
    changed = Signal()

    def __init__(self, app_ctx) -> None:
        super().__init__()
        self.app_ctx = app_ctx
        self.room_id: int | None = None
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, 720, 420)

        self.view = PlannerView(self, self.scene)
        self.view.setMinimumHeight(330)
        self._markers: dict[int, PlanMarker] = {}

        self.spin_ceiling = QSpinBox()
        self.spin_spot = QSpinBox()
        self.spin_network = QSpinBox()
        self.spin_outdoor = QSpinBox()
        for s in [self.spin_ceiling, self.spin_spot, self.spin_network, self.spin_outdoor]:
            s.setRange(0, 99)

        self.room_title = QLabel("Raumplanung")
        self.apply_btn = QPushButton("Mengen übernehmen")
        self.apply_btn.clicked.connect(self.apply_counts)

        controls = QFormLayout()
        controls.addRow("Deckenlicht", self.spin_ceiling)
        controls.addRow("Spotlights", self.spin_spot)
        controls.addRow("Netzwerkdosen", self.spin_network)
        controls.addRow("Außenlicht", self.spin_outdoor)

        left = QVBoxLayout()
        left.addWidget(self.room_title)
        left.addLayout(controls)
        left.addWidget(self.apply_btn)
        left.addStretch(1)

        layout = QHBoxLayout(self)
        left_wrap = QWidget()
        left_wrap.setLayout(left)
        layout.addWidget(left_wrap)
        layout.addWidget(self.view, 1)

    def set_room(self, room_id: int) -> None:
        self.room_id = room_id
        with self.app_ctx.db.session() as session:
            room = session.get(Room, room_id)
            self.room_title.setText(f"Raumplanung: {room.name if room else room_id}")
        self.reload()

    def color_for(self, plan_type: PlanItemType) -> str:
        return {
            PlanItemType.CEILING_LIGHT: "#60a5fa",
            PlanItemType.SPOTLIGHT: "#f59e0b",
            PlanItemType.NETWORK_SOCKET: "#10b981",
            PlanItemType.OUTDOOR_LIGHT: "#f97316",
        }[plan_type]

    def reload(self) -> None:
        self.scene.clear()
        self._markers.clear()
        if self.room_id is None:
            return
        with self.app_ctx.db.session() as session:
            plans = session.query(RoomPlanItem).filter(RoomPlanItem.room_id == self.room_id).all()

        counts = Counter(p.item_type for p in plans)
        self.spin_ceiling.setValue(counts[PlanItemType.CEILING_LIGHT])
        self.spin_spot.setValue(counts[PlanItemType.SPOTLIGHT])
        self.spin_network.setValue(counts[PlanItemType.NETWORK_SOCKET])
        self.spin_outdoor.setValue(counts[PlanItemType.OUTDOOR_LIGHT])

        for p in plans:
            marker = PlanMarker(p, self.color_for(p.item_type))
            marker.setPos(QPointF(p.pos_x, p.pos_y))
            self.scene.addItem(marker)
            self._markers[p.id] = marker

    def apply_counts(self) -> None:
        if self.room_id is None:
            return
        target = {
            PlanItemType.CEILING_LIGHT: self.spin_ceiling.value(),
            PlanItemType.SPOTLIGHT: self.spin_spot.value(),
            PlanItemType.NETWORK_SOCKET: self.spin_network.value(),
            PlanItemType.OUTDOOR_LIGHT: self.spin_outdoor.value(),
        }
        with self.app_ctx.db.session() as session:
            plans = session.query(RoomPlanItem).filter(RoomPlanItem.room_id == self.room_id).all()
            by_type: dict[PlanItemType, list[RoomPlanItem]] = {}
            for p in plans:
                by_type.setdefault(p.item_type, []).append(p)

            for plan_type, desired in target.items():
                current = by_type.get(plan_type, [])
                if len(current) > desired:
                    for item in current[desired:]:
                        session.delete(item)
                elif len(current) < desired:
                    for idx in range(len(current), desired):
                        session.add(
                            RoomPlanItem(
                                room_id=self.room_id,
                                item_type=plan_type,
                                label=f"{plan_type.value}-{idx + 1}",
                                pos_x=70 + (idx % 6) * 90,
                                pos_y=70 + (idx // 6) * 75,
                            )
                        )
        self.reload()
        self.changed.emit()

    def persist_positions(self) -> None:
        if self.room_id is None:
            return
        with self.app_ctx.db.session() as session:
            for plan_id, marker in self._markers.items():
                plan = session.get(RoomPlanItem, plan_id)
                if plan:
                    plan.pos_x = max(0.0, marker.pos().x())
                    plan.pos_y = max(0.0, marker.pos().y())

