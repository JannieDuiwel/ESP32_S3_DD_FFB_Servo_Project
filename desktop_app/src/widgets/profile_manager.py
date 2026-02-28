"""Profile manager — save/load/export settings as JSON files."""
import json
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QListWidget, QFileDialog, QInputDialog, QMessageBox,
)

PROFILES_DIR = os.path.join(os.path.expanduser("~"), ".ffb_companion", "profiles")


class ProfileManager(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main_window = main_window
        os.makedirs(PROFILES_DIR, exist_ok=True)
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Profile list
        list_group = QGroupBox("Saved Profiles")
        ll = QVBoxLayout(list_group)

        self._list = QListWidget()
        ll.addWidget(self._list)

        btn_row = QHBoxLayout()
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self._load_profile)
        save_btn = QPushButton("Save Current")
        save_btn.clicked.connect(self._save_profile)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_profile)
        btn_row.addWidget(load_btn)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(delete_btn)
        ll.addLayout(btn_row)
        layout.addWidget(list_group)

        # Import/Export
        io_group = QGroupBox("Import / Export")
        il = QHBoxLayout(io_group)
        export_btn = QPushButton("Export to File...")
        export_btn.clicked.connect(self._export_profile)
        import_btn = QPushButton("Import from File...")
        import_btn.clicked.connect(self._import_profile)
        il.addWidget(export_btn)
        il.addWidget(import_btn)
        layout.addWidget(io_group)

        layout.addStretch()

    def _refresh_list(self):
        self._list.clear()
        if os.path.isdir(PROFILES_DIR):
            for f in sorted(os.listdir(PROFILES_DIR)):
                if f.endswith(".json"):
                    self._list.addItem(f[:-5])

    def _save_profile(self):
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        settings = self._main_window.get_all_settings()
        path = os.path.join(PROFILES_DIR, f"{name}.json")
        with open(path, "w") as f:
            json.dump(settings, f, indent=2)
        self._refresh_list()

    def _load_profile(self):
        item = self._list.currentItem()
        if not item:
            return
        path = os.path.join(PROFILES_DIR, f"{item.text()}.json")
        with open(path) as f:
            settings = json.load(f)
        self._main_window.apply_all_settings(settings)

    def _delete_profile(self):
        item = self._list.currentItem()
        if not item:
            return
        reply = QMessageBox.question(
            self, "Delete Profile",
            f"Delete profile '{item.text()}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            path = os.path.join(PROFILES_DIR, f"{item.text()}.json")
            os.remove(path)
            self._refresh_list()

    def _export_profile(self):
        item = self._list.currentItem()
        if not item:
            settings = self._main_window.get_all_settings()
        else:
            path = os.path.join(PROFILES_DIR, f"{item.text()}.json")
            with open(path) as f:
                settings = json.load(f)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Profile", "", "JSON Files (*.json)"
        )
        if file_path:
            with open(file_path, "w") as f:
                json.dump(settings, f, indent=2)

    def _import_profile(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Profile", "", "JSON Files (*.json)"
        )
        if not file_path:
            return
        with open(file_path) as f:
            settings = json.load(f)
        name = os.path.splitext(os.path.basename(file_path))[0]
        dest = os.path.join(PROFILES_DIR, f"{name}.json")
        with open(dest, "w") as f:
            json.dump(settings, f, indent=2)
        self._refresh_list()
