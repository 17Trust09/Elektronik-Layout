from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from models.schema import Circuit, Device, Endpoint, Room


class InspectorWidget(QWidget):
    def __init__(self, app_ctx) -> None:
        super().__init__()
        self.app_ctx = app_ctx
        self.current: tuple[str, int] | None = None
        layout = QVBoxLayout(self)
        self.title = QLabel("Inspector")
        layout.addWidget(self.title)
        self.form = QFormLayout()
        layout.addLayout(self.form)
        self.name_edit = QLineEdit()
        self.extra_edit = QLineEdit()
        self.notes_edit = QTextEdit()
        self.form.addRow("Name/Label", self.name_edit)
        self.form.addRow("Extra", self.extra_edit)
        self.form.addRow("Notes", self.notes_edit)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save)
        layout.addWidget(self.save_btn)

    def load_entity(self, entity: str, entity_id: int) -> None:
        self.current = (entity, entity_id)
        with self.app_ctx.db.session() as session:
            obj = session.get({"device": Device, "circuit": Circuit, "room": Room, "endpoint": Endpoint}.get(entity, Device), entity_id)
            if not obj:
                return
            name = getattr(obj, "label", None) or getattr(obj, "name", None) or getattr(obj, "description", "")
            self.name_edit.setText(name)
            self.extra_edit.setText(getattr(obj, "rating", "") or getattr(obj, "floor", "") or "")
            self.notes_edit.setPlainText(getattr(obj, "notes", ""))

    def save(self) -> None:
        if not self.current:
            return
        entity, entity_id = self.current
        try:
            with self.app_ctx.db.session() as session:
                cls_map = {"device": Device, "circuit": Circuit, "room": Room, "endpoint": Endpoint}
                obj = session.get(cls_map[entity], entity_id)
                if not obj:
                    return
                if hasattr(obj, "label"):
                    obj.label = self.name_edit.text()
                elif hasattr(obj, "name"):
                    obj.name = self.name_edit.text()
                else:
                    obj.description = self.name_edit.text()
                if hasattr(obj, "rating"):
                    obj.rating = self.extra_edit.text()
                if hasattr(obj, "floor"):
                    obj.floor = self.extra_edit.text()
                obj.notes = self.notes_edit.toPlainText()
            self.app_ctx.data_changed.emit()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Speichern fehlgeschlagen: {exc}")
