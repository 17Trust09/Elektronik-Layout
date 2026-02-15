from __future__ import annotations

import logging
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
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

from models.schema import Circuit, Device, DeviceType, Endpoint, Panel, Room
from services.export_service import ExportService
from ui.graph_view import GraphView
from ui.inspector import InspectorWidget
from ui.panel_view import PanelView
from ui.rcd_mapping_wizard import RcdMappingWizard
from ui.test_mode_wizard import TestModeWizard

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, app_ctx) -> None:
        super().__init__()
        self.app_ctx = app_ctx
        self.setWindowTitle("StromkreisDoku")
        self.resize(1600, 900)
        self.export_service = ExportService(Path("assets/templates"))

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
        top_row = QHBoxLayout()
        self.export_btn = QPushButton("Export HTML")
        self.export_btn.clicked.connect(self.export_html)
        self.export_json_btn = QPushButton("Export JSON")
        self.export_json_btn.clicked.connect(self.export_json)
        self.import_json_btn = QPushButton("Import JSON")
        self.import_json_btn.clicked.connect(self.import_json_info)
        self.open_report_btn = QPushButton("Open Report")
        self.open_report_btn.clicked.connect(self.open_report)
        self.rcd_btn = QPushButton("RCD Wizard")
        self.rcd_btn.clicked.connect(self.open_rcd_wizard)
        self.test_mode_btn = QPushButton("Test Mode")
        self.test_mode_btn.clicked.connect(self.open_test_mode)
        self.fit_graph_btn = QPushButton("Fit Graph")
        self.fit_graph_btn.clicked.connect(self.graph_view_fit)

        self.filter_uncertain = QCheckBox("Nur Unknown/Likely")
        self.filter_uncertain.stateChanged.connect(self.apply_graph_filters)
        for w in [self.export_btn, self.export_json_btn, self.import_json_btn, self.open_report_btn, self.rcd_btn, self.test_mode_btn, self.fit_graph_btn, self.filter_uncertain]:
            top_row.addWidget(w)

        self.tabs = QTabWidget()
        self.panel_view = PanelView(app_ctx)
        self.graph_view = GraphView(app_ctx)
        self.rooms_table = QTreeWidget()
        self.rooms_table.setHeaderLabels(["Room", "Floor"])
        self.tabs.addTab(self.panel_view, "PanelView")
        self.tabs.addTab(self.graph_view, "GraphView")
        self.tabs.addTab(self.rooms_table, "Rooms")
        center_layout.addLayout(top_row)
        center_layout.addWidget(self.tabs)

        self.inspector = InspectorWidget(app_ctx)
        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(self.inspector)
        splitter.setSizes([320, 930, 350])

        status = QStatusBar()
        self.status_project = QLabel(f"Projekt: {self.app_ctx.project_dir}")
        self.status_selection = QLabel("Selection: -")
        self.status_filter = QLabel("Filter: all")
        self.status_dirty = QLabel("Clean")
        for label in [self.status_project, self.status_selection, self.status_filter, self.status_dirty]:
            status.addWidget(label)
        self.setStatusBar(status)

        self.nav_tree.itemClicked.connect(self.on_nav_clicked)
        self.panel_view.entity_selected.connect(self.app_ctx.select)
        self.graph_view.node_selected.connect(self.app_ctx.select)
        self.panel_view.assign_rcd_requested.connect(self.open_rcd_wizard)
        self.app_ctx.selection_changed.connect(self.on_selection_changed)
        self.app_ctx.selection_changed.connect(self.inspector.load_entity)
        self.app_ctx.data_changed.connect(self.refresh_all)

        self.refresh_all()

    def refresh_all(self) -> None:
        self.refresh_nav()
        self.refresh_rooms()
        self.panel_view.refresh()
        self.apply_graph_filters()
        self.status_dirty.setText("Saved")

    def refresh_nav(self) -> None:
        self.nav_tree.clear()
        with self.app_ctx.db.session() as session:
            panel_root = QTreeWidgetItem(["Panels"])
            self.nav_tree.addTopLevelItem(panel_root)
            for panel in session.query(Panel).all():
                panel_item = QTreeWidgetItem([panel.name])
                panel_item.setData(0, Qt.ItemDataRole.UserRole, ("panel", panel.id))
                panel_root.addChild(panel_item)
                for d in session.query(Device).filter(Device.panel_id == panel.id).all():
                    item = QTreeWidgetItem([f"{d.type.value}: {d.label}"])
                    item.setData(0, Qt.ItemDataRole.UserRole, ("device", d.id))
                    panel_item.addChild(item)

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
            for room in session.query(Room).all():
                r_item = QTreeWidgetItem([room.name])
                r_item.setData(0, Qt.ItemDataRole.UserRole, ("room", room.id))
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
            self.app_ctx.select(*payload)

    def on_selection_changed(self, entity: str, entity_id: int) -> None:
        self.status_selection.setText(f"Selection: {entity}#{entity_id}")
        self.panel_view.set_highlight(entity, entity_id)
        self.graph_view.set_highlight(entity, entity_id)
        self.apply_graph_filters()

    def apply_graph_filters(self) -> None:
        selected_device: int | None = None
        selected_type, selected_id = self.app_ctx.current_selection
        if selected_type == "device":
            with self.app_ctx.db.session() as session:
                dev = session.get(Device, selected_id)
                if dev and dev.type in {DeviceType.RCD, DeviceType.MCB}:
                    selected_device = dev.id
        self.graph_view.set_filters(self.filter_uncertain.isChecked(), selected_device)
        self.status_filter.setText("Filter: uncertain" if self.filter_uncertain.isChecked() else "Filter: all")

    def graph_view_fit(self) -> None:
        self.graph_view.fit_graph()

    def add_room(self) -> None:
        with self.app_ctx.db.session() as session:
            session.add(Room(name="Neuer Raum", floor="EG"))
        self.status_dirty.setText("Dirty")
        self.app_ctx.data_changed.emit()

    def delete_selected(self) -> None:
        item = self.nav_tree.currentItem()
        if item is None:
            return
        payload = item.data(0, Qt.ItemDataRole.UserRole)
        if not payload:
            return
        entity, entity_id = payload
        cls_map = {"device": Device, "circuit": Circuit, "endpoint": Endpoint, "room": Room, "panel": Panel}
        cls = cls_map.get(entity)
        if cls is None:
            return
        with self.app_ctx.db.session() as session:
            obj = session.get(cls, entity_id)
            if obj:
                session.delete(obj)
        self.status_dirty.setText("Dirty")
        self.app_ctx.data_changed.emit()

    def open_rcd_wizard(self) -> None:
        RcdMappingWizard(self.app_ctx, self).exec()

    def open_test_mode(self) -> None:
        TestModeWizard(self.app_ctx, self).exec()

    def export_html(self) -> None:
        try:
            export_file = self.app_ctx.project_dir / "exports" / "report.html"
            with self.app_ctx.db.session() as session:
                self.export_service.export_html(session, export_file, Path("assets/styles/report.css"))
            self.statusBar().showMessage(f"Exportiert: {export_file}", 5000)
        except Exception as exc:
            LOGGER.exception("Export failed")
            QMessageBox.critical(self, "Export Fehler", str(exc))

    def export_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "JSON export", str(self.app_ctx.project_dir / "project.json"), "JSON (*.json)")
        if not path:
            return
        with self.app_ctx.db.session() as session:
            self.export_service.export_json(session, Path(path))
        self.statusBar().showMessage(f"JSON exportiert: {path}", 4000)

    def import_json_info(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "JSON import", str(self.app_ctx.project_dir), "JSON (*.json)")
        if not path:
            return
        try:
            with self.app_ctx.db.session() as session:
                self.export_service.import_json(session, Path(path))
            self.statusBar().showMessage(f"JSON importiert: {path}", 4000)
            self.app_ctx.data_changed.emit()
        except Exception as exc:
            LOGGER.exception("JSON import failed")
            QMessageBox.critical(self, "Import Fehler", str(exc))

    def open_report(self) -> None:
        report = self.app_ctx.project_dir / "exports" / "report.html"
        if not report.exists():
            QMessageBox.warning(self, "Hinweis", "Report noch nicht exportiert")
            return
        webbrowser.open(report.as_uri())
