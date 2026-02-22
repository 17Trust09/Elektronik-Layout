from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from models.schema import Device, DeviceType, ProtectionLink


class RcdMappingWizard(QDialog):
    def __init__(self, app_ctx, parent=None) -> None:
        super().__init__(parent)
        self.app_ctx = app_ctx
        self.setWindowTitle("RCD Mapping Wizard")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("RCD wählen"))
        self.rcd_combo = QComboBox()
        self.mcb_checks: list[tuple[int, QCheckBox]] = []
        layout.addWidget(self.rcd_combo)
        layout.addWidget(QLabel("MCBs zuordnen"))

        with self.app_ctx.db.session() as session:
            rcds = session.query(Device).filter(Device.type == DeviceType.RCD).all()
            mcbs = session.query(Device).filter(Device.type == DeviceType.MCB).all()
            for rcd in rcds:
                self.rcd_combo.addItem(rcd.label, rcd.id)
            for mcb in mcbs:
                check = QCheckBox(mcb.label)
                layout.addWidget(check)
                self.mcb_checks.append((mcb.id, check))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._load_selected()
        self.rcd_combo.currentIndexChanged.connect(self._load_selected)

    def _load_selected(self) -> None:
        rcd_id = self.rcd_combo.currentData()
        with self.app_ctx.db.session() as session:
            linked = {l.mcb_device_id for l in session.query(ProtectionLink).filter(ProtectionLink.rcd_device_id == rcd_id).all()}
            for mcb_id, check in self.mcb_checks:
                check.setChecked(mcb_id in linked)

    def save(self) -> None:
        rcd_id = self.rcd_combo.currentData()
        selected = {mcb_id for mcb_id, check in self.mcb_checks if check.isChecked()}
        with self.app_ctx.db.session() as session:
            existing = session.query(ProtectionLink).filter(ProtectionLink.rcd_device_id == rcd_id).all()
            existing_ids = {l.mcb_device_id for l in existing}
            for link in existing:
                if link.mcb_device_id not in selected:
                    session.delete(link)
            for mcb_id in selected - existing_ids:
                session.add(ProtectionLink(rcd_device_id=rcd_id, mcb_device_id=mcb_id))
        self.app_ctx.data_changed.emit()
        self.accept()
