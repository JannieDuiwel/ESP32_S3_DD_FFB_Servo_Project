"""Safety panel — enable/disable, max torque, fault display."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QGroupBox,
    QPushButton, QTextEdit,
)
from PySide6.QtCore import Qt
from protocol import FAULT_NAMES


class SafetyPanel(QWidget):
    def __init__(self, serial_comm, parent=None):
        super().__init__(parent)
        self._serial = serial_comm
        self._enabled = False
        self._setup_ui()
        self._serial.fault_received.connect(self._on_fault)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Enable/Disable toggle
        enable_group = QGroupBox("Motor Control")
        el = QHBoxLayout(enable_group)
        self._enable_btn = QPushButton("ENABLE")
        self._enable_btn.setFixedSize(200, 60)
        self._enable_btn.setStyleSheet(
            "QPushButton { background-color: #2d5a2d; color: white; font-size: 18px; font-weight: bold; }"
            "QPushButton:hover { background-color: #3a7a3a; }"
        )
        self._enable_btn.clicked.connect(self._toggle_enable)
        el.addWidget(self._enable_btn)
        el.addStretch()
        layout.addWidget(enable_group)

        # Max torque
        torque_group = QGroupBox("Max Torque Limit")
        tl = QHBoxLayout(torque_group)
        tl.addWidget(QLabel("0%"))
        self._torque_slider = QSlider(Qt.Horizontal)
        self._torque_slider.setRange(0, 100)
        self._torque_slider.setValue(75)
        self._torque_label = QLabel("75%")
        self._torque_slider.valueChanged.connect(
            lambda v: self._torque_label.setText(f"{v}%")
        )
        tl.addWidget(self._torque_slider)
        tl.addWidget(QLabel("100%"))
        tl.addWidget(self._torque_label)
        layout.addWidget(torque_group)

        # Fault log
        fault_group = QGroupBox("Fault Log")
        fl = QVBoxLayout(fault_group)
        self._fault_log = QTextEdit()
        self._fault_log.setReadOnly(True)
        self._fault_log.setMaximumHeight(200)
        fl.addWidget(self._fault_log)

        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self._fault_log.clear)
        fl.addWidget(clear_btn)
        layout.addWidget(fault_group)

        layout.addStretch()

    def _toggle_enable(self):
        self._enabled = not self._enabled
        self._serial.send_enable(self._enabled)
        if self._enabled:
            self._enable_btn.setText("DISABLE")
            self._enable_btn.setStyleSheet(
                "QPushButton { background-color: #8b2020; color: white; font-size: 18px; font-weight: bold; }"
                "QPushButton:hover { background-color: #a52a2a; }"
            )
        else:
            self._enable_btn.setText("ENABLE")
            self._enable_btn.setStyleSheet(
                "QPushButton { background-color: #2d5a2d; color: white; font-size: 18px; font-weight: bold; }"
                "QPushButton:hover { background-color: #3a7a3a; }"
            )

    def _on_fault(self, code: int, name: str):
        self._fault_log.append(f"FAULT 0x{code:02X}: {name}")
        # Auto-disable on fault
        if self._enabled:
            self._toggle_enable()

    def get_settings(self) -> dict:
        return {"max_torque_percent": self._torque_slider.value()}

    def apply_settings(self, settings: dict):
        if "max_torque_percent" in settings:
            self._torque_slider.setValue(settings["max_torque_percent"])
