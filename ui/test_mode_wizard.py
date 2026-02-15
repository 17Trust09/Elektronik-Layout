from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from models.schema import Circuit, ConfidenceType, Endpoint, Room


class TestModeWizard(QDialog):
    def __init__(self, app_ctx, parent=None) -> None:
        super().__init__(parent)
        self.app_ctx = app_ctx
        self.setWindowTitle("Test Mode Wizard")
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Stromkreis wählen"))
        self.circuit_combo = QComboBox()
        layout.addWidget(self.circuit_combo)

        layout.addWidget(QLabel("OFF bestätigt (LS aus) je Endpoint"))
        self.endpoint_checks: list[tuple[int, QCheckBox]] = []
        self.group_label = QLabel()
        layout.addWidget(self.group_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        with self.app_ctx.db.session() as session:
            for circuit in session.query(Circuit).all():
                self.circuit_combo.addItem(circuit.name, circuit.id)

        self.circuit_combo.currentIndexChanged.connect(self._reload_endpoints)
        self._reload_endpoints()

    def _reload_endpoints(self) -> None:
        while self.endpoint_checks:
            _, check = self.endpoint_checks.pop()
            check.setParent(None)

        circuit_id = self.circuit_combo.currentData()
        if circuit_id is None:
            self.group_label.setText("Keine Stromkreise vorhanden")
            return

        with self.app_ctx.db.session() as session:
            endpoints = session.query(Endpoint).filter(Endpoint.circuit_id == circuit_id).all()
            room_map = {r.id: r for r in session.query(Room).all()}

        self.group_label.setText(f"{len(endpoints)} Endpoints")
        for endpoint in endpoints:
            room_name = room_map.get(endpoint.room_id).name if endpoint.room_id in room_map else "Unbekannt"
            check = QCheckBox(f"[{room_name}] {endpoint.description or endpoint.type.value}")
            check.setChecked(endpoint.confidence == ConfidenceType.CONFIRMED)
            self.layout().insertWidget(self.layout().count() - 1, check)
            self.endpoint_checks.append((endpoint.id, check))

    def save(self) -> None:
        today = date.today().isoformat()
        with self.app_ctx.db.session() as session:
            for endpoint_id, check in self.endpoint_checks:
                endpoint = session.get(Endpoint, endpoint_id)
                if endpoint is None:
                    continue
                if check.isChecked():
                    endpoint.confidence = ConfidenceType.CONFIRMED
                    note = f"verified on {today} (LS-Off)"
                    endpoint.notes = f"{endpoint.notes}\n{note}".strip()
                elif endpoint.confidence == ConfidenceType.CONFIRMED:
                    endpoint.confidence = ConfidenceType.LIKELY
        self.app_ctx.data_changed.emit()
        self.accept()
