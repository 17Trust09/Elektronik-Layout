from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from services.database import Database
from services.project_fs import ProjectFS


class AppContext(QObject):
    selection_changed = Signal(str, int)
    data_changed = Signal()

    def __init__(self, project_dir: Path) -> None:
        super().__init__()
        self.project_dir = project_dir
        self.project_fs = ProjectFS(project_dir)
        self.db: Database = self.project_fs.ensure()
        self._selected_type: str = ""
        self._selected_id: int = 0
        self.setup_logging()

    def setup_logging(self) -> None:
        log_path = self.project_fs.logs_dir / "app.log"
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
        )

    def select(self, entity: str, entity_id: int) -> None:
        self._selected_type, self._selected_id = entity, entity_id
        self.selection_changed.emit(entity, entity_id)

    @property
    def current_selection(self) -> tuple[str, int]:
        return self._selected_type, self._selected_id
