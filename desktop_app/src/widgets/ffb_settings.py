"""FFB gain settings — global gain and per-effect-type sliders."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QGroupBox, QPushButton,
)
from PySide6.QtCore import Qt


EFFECT_TYPES = [
    "Constant Force",
    "Spring",
    "Damper",
    "Friction",
    "Inertia",
    "Periodic",
]


class FFBSettings(QWidget):
    def __init__(self, serial_comm, parent=None):
        super().__init__(parent)
        self._serial = serial_comm
        self._sliders = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Global gain
        global_group = QGroupBox("Global FFB Gain")
        gl = QHBoxLayout(global_group)

        self._global_label = QLabel("50%")
        self._global_slider = QSlider(Qt.Horizontal)
        self._global_slider.setRange(0, 100)
        self._global_slider.setValue(50)
        self._global_slider.valueChanged.connect(self._on_global_gain)

        gl.addWidget(QLabel("0"))
        gl.addWidget(self._global_slider)
        gl.addWidget(QLabel("100"))
        gl.addWidget(self._global_label)
        layout.addWidget(global_group)

        # Per-effect gains (for future use — stored locally, applied when firmware supports it)
        effects_group = QGroupBox("Per-Effect Gain (Future)")
        el = QVBoxLayout(effects_group)

        for name in EFFECT_TYPES:
            row = QHBoxLayout()
            label = QLabel(f"{name}:")
            label.setMinimumWidth(120)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(100)
            val_label = QLabel("100%")
            slider.valueChanged.connect(
                lambda v, lbl=val_label: lbl.setText(f"{v}%")
            )
            self._sliders[name] = slider

            row.addWidget(label)
            row.addWidget(slider)
            row.addWidget(val_label)
            el.addLayout(row)

        layout.addWidget(effects_group)

        # Test buttons
        test_group = QGroupBox("Test Effects")
        tl = QHBoxLayout(test_group)
        for label_text in ["Center Spring", "Constant Left", "Constant Right", "Sine Wave"]:
            btn = QPushButton(label_text)
            btn.setEnabled(False)  # Placeholder until firmware supports test effects
            tl.addWidget(btn)
        layout.addWidget(test_group)

        layout.addStretch()

    def _on_global_gain(self, value: int):
        self._global_label.setText(f"{value}%")
        self._serial.send_gain(value)

    def get_settings(self) -> dict:
        return {
            "global_gain": self._global_slider.value(),
            "effects": {name: s.value() for name, s in self._sliders.items()},
        }

    def apply_settings(self, settings: dict):
        if "global_gain" in settings:
            self._global_slider.setValue(settings["global_gain"])
        for name, val in settings.get("effects", {}).items():
            if name in self._sliders:
                self._sliders[name].setValue(val)
