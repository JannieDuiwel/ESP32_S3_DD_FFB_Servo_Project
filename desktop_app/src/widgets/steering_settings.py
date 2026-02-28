"""Steering configuration — rotation range, center calibration, dead zone."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QGroupBox,
    QPushButton, QSpinBox,
)
from PySide6.QtCore import Qt


class SteeringSettings(QWidget):
    def __init__(self, serial_comm, parent=None):
        super().__init__(parent)
        self._serial = serial_comm
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Rotation range
        range_group = QGroupBox("Rotation Range")
        rl = QVBoxLayout(range_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Total Degrees:"))
        self._rotation_spin = QSpinBox()
        self._rotation_spin.setRange(180, 1080)
        self._rotation_spin.setSingleStep(10)
        self._rotation_spin.setValue(900)
        self._rotation_label = QLabel("(+/- 450)")
        self._rotation_spin.valueChanged.connect(
            lambda v: self._rotation_label.setText(f"(+/- {v // 2})")
        )
        row1.addWidget(self._rotation_spin)
        row1.addWidget(self._rotation_label)
        row1.addStretch()
        rl.addLayout(row1)

        # Quick presets
        row2 = QHBoxLayout()
        for deg in [360, 540, 720, 900, 1080]:
            btn = QPushButton(f"{deg}")
            btn.setFixedWidth(60)
            btn.clicked.connect(lambda _, d=deg: self._rotation_spin.setValue(d))
            row2.addWidget(btn)
        row2.addStretch()
        rl.addLayout(row2)

        layout.addWidget(range_group)

        # Dead zone
        dz_group = QGroupBox("Dead Zone")
        dl = QHBoxLayout(dz_group)
        dl.addWidget(QLabel("Center:"))
        self._deadzone_slider = QSlider(Qt.Horizontal)
        self._deadzone_slider.setRange(0, 20)
        self._deadzone_slider.setValue(0)
        self._deadzone_label = QLabel("0%")
        self._deadzone_slider.valueChanged.connect(
            lambda v: self._deadzone_label.setText(f"{v}%")
        )
        dl.addWidget(self._deadzone_slider)
        dl.addWidget(self._deadzone_label)
        layout.addWidget(dz_group)

        # Calibration
        cal_group = QGroupBox("Calibration")
        cl = QHBoxLayout(cal_group)
        self._center_btn = QPushButton("Set Center")
        self._center_btn.clicked.connect(self._on_set_center)
        cl.addWidget(self._center_btn)
        cl.addWidget(QLabel("Hold wheel at center position, then click"))
        cl.addStretch()
        layout.addWidget(cal_group)

        layout.addStretch()

    def _on_set_center(self):
        # TODO: send calibration command to firmware
        self._center_btn.setText("Center Set!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self._center_btn.setText("Set Center"))

    def get_settings(self) -> dict:
        return {
            "rotation_degrees": self._rotation_spin.value(),
            "deadzone_percent": self._deadzone_slider.value(),
        }

    def apply_settings(self, settings: dict):
        if "rotation_degrees" in settings:
            self._rotation_spin.setValue(settings["rotation_degrees"])
        if "deadzone_percent" in settings:
            self._deadzone_slider.setValue(settings["deadzone_percent"])
