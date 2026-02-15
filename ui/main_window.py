from __future__ import annotations

import logging
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.schema import Circuit, Device, Endpoint, Panel, Room
from services.export_service import ExportService
from ui.graph_view import GraphView
from ui.inspector import InspectorWidget
from ui.panel_view import PanelView
from ui.rcd_mapping_wizard import RcdMappingWizard

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, app_ctx) -> None:
        super().__init__()
        self.app_ctx = app_ctx
        self.setWindowTitle("StromkreisDoku")
        self.resize(1600, 900)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderLabel("Navigation")
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.add_room_btn = QPushButton("Add Room")
        self.add_room_btn.clicked.connect(self.add_room)
        self.del_btn = QPushButton("Delete Selected")
        self.del_btn.clicked.connect(self.delete_selected)
        left_layout.addWidget(self.add_room_btn)
        left_layout.addWidget(self.del_btn)
        left_layout.addWidget(self.nav_tree)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        button_row = QHBoxLayout()
        self.export_btn = QPushButton("Export HTML")
        self.export_btn.clicked.connect(self.export_html)
        self.open_report_btn = QPushButton("Open Report")
        self.open_report_btn.clicked.connect(self.open_report)
        self.rcd_btn = QPushButton("RCD Wizard")
        self.rcd_btn.clicked.connect(self.open_rcd_wizard)
        button_row.addWidget(self.export_btn)
        button_row.addWidget(self.open_report_btn)
        button_row.addWidget(self.rcd_btn)

        self.tabs = QTabWidget()
        self.panel_view = PanelView(app_ctx)
        self.graph_view = GraphView(app_ctx)
        self.rooms_table = QTreeWidget()
        self.rooms_table.setHeaderLabels(["Room", "Floor"])
        self.tabs.addTab(self.panel_view, "PanelView")
        self.tabs.addTab(self.graph_view, "GraphView")
        self.tabs.addTab(self.rooms_table, "Rooms")
        center_layout.addLayout(button_row)
        center_layout.addWidget(self.tabs)

        self.inspector = InspectorWidget(app_ctx)

        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(self.inspector)
        splitter.setSizes([300, 950, 350])

        status = QStatusBar()
        self.status_info = QLabel(f"Project: {self.app_ctx.project_dir}")
        status.addWidget(self.status_info)
        self.setStatusBar(status)

        self.nav_tree.itemClicked.connect(self.on_nav_clicked)
        self.panel_view.device_selected.connect(lambda did: self.app_ctx.select("device", did))
        self.graph_view.node_selected.connect(self.app_ctx.select)
        self.panel_view.assign_rcd_requested.connect(self.open_rcd_wizard)
        self.app_ctx.selection_changed.connect(self.inspector.load_entity)
        self.app_ctx.data_changed.connect(self.refresh_all)

        self.refresh_all()

    def refresh_all(self) -> None:
        self.refresh_nav()
        self.refresh_rooms()
        self.panel_view.refresh()
        self.graph_view.refresh()

    def refresh_nav(self) -> None:
        self.nav_tree.clear()
        with self.app_ctx.db.session() as session:
            panel_root = QTreeWidgetItem(["Panels"])
            self.nav_tree.addTopLevelItem(panel_root)
            for p in session.query(Panel).all():
                p_item = QTreeWidgetItem([p.name])
                p_item.setData(0, Qt.ItemDataRole.UserRole, ("panel", p.id))
                panel_root.addChild(p_item)
                for d in session.query(Device).filter(Device.panel_id == p.id).all():
                    child = QTreeWidgetItem([f"{d.type.value}: {d.label}"])
                    child.setData(0, Qt.ItemDataRole.UserRole, ("device", d.id))
                    p_item.addChild(child)

            circuit_root = QTreeWidgetItem(["Circuits"])
            self.nav_tree.addTopLevelItem(circuit_root)
            for c in session.query(Circuit).all():
                c_item = QTreeWidgetItem([c.name])
                c_item.setData(0, Qt.ItemDataRole.UserRole, ("circuit", c.id))
                circuit_root.addChild(c_item)
                for e in session.query(Endpoint).filter(Endpoint.circuit_id == c.id).all():
                    e_item = QTreeWidgetItem([e.description])
                    e_item.setData(0, Qt.ItemDataRole.UserRole, ("endpoint", e.id))
                    c_item.addChild(e_item)

            room_root = QTreeWidgetItem(["Rooms"])
            self.nav_tree.addTopLevelItem(room_root)
            for r in session.query(Room).all():
                r_item = QTreeWidgetItem([r.name])
                r_item.setData(0, Qt.ItemDataRole.UserRole, ("room", r.id))
                room_root.addChild(r_item)
            self.nav_tree.expandAll()

    def refresh_rooms(self) -> None:
        self.rooms_table.clear()
        with self.app_ctx.db.session() as session:
            for room in session.query(Room).all():
                self.rooms_table.addTopLevelItem(QTreeWidgetItem([room.name, room.floor]))

    def on_nav_clicked(self, item: QTreeWidgetItem) -> None:
        payload = item.data(0, Qt.ItemDataRole.UserRole)
        if payload:
            entity, entity_id = payload
            self.app_ctx.select(entity, entity_id)

    def add_room(self) -> None:
        with self.app_ctx.db.session() as session:
            session.add(Room(name="Neuer Raum", floor="EG"))
        self.app_ctx.data_changed.emit()

    def delete_selected(self) -> None:
        item = self.nav_tree.currentItem()
        if not item:
            return
        payload = item.data(0, Qt.ItemDataRole.UserRole)
        if not payload:
            return
        entity, entity_id = payload
        cls_map = {"device": Device, "circuit": Circuit, "endpoint": Endpoint, "room": Room, "panel": Panel}
        cls = cls_map.get(entity)
        if not cls:
            return
        with self.app_ctx.db.session() as session:
            obj = session.get(cls, entity_id)
            if obj:
                session.delete(obj)
        self.app_ctx.data_changed.emit()

    def open_rcd_wizard(self) -> None:
        wizard = RcdMappingWizard(self.app_ctx, self)
        wizard.exec()

    def export_html(self) -> None:
        try:
            export_dir = self.app_ctx.project_dir / "exports"
            export_file = export_dir / "report.html"
            service = ExportService(Path("assets/templates"))
            with self.app_ctx.db.session() as session:
                service.export_html(session, export_file, Path("assets/styles/report.css"))
            self.statusBar().showMessage(f"Exportiert: {export_file}", 5000)
        except Exception as exc:
            LOGGER.exception("Export failed")
            QMessageBox.critical(self, "Export Fehler", str(exc))

    def open_report(self) -> None:
        report = self.app_ctx.project_dir / "exports" / "report.html"
        if not report.exists():
            QMessageBox.warning(self, "Hinweis", "Report noch nicht exportiert")
            return
        webbrowser.open(report.as_uri())
