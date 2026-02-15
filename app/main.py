from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from app.context import AppContext
from ui.main_window import MainWindow


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative


def main() -> int:
    app = QApplication(sys.argv)
    project_dir = Path.cwd() / "demo_project"
    ctx = AppContext(project_dir)

    qss = resource_path("assets/theme_dark.qss")
    if qss.exists():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))

    try:
        window = MainWindow(ctx)
        window.show()
        return app.exec()
    except Exception as exc:
        QMessageBox.critical(None, "Startup error", str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
