"""Pedal calibration — response curve editor with interactive graph."""
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QComboBox, QSlider,
)
from PySide6.QtCore import Qt


def linear_curve(x):
    return x

def gamma_curve(x, gamma=2.2):
    return np.power(x, gamma)

def s_curve(x, steepness=5.0):
    return 1.0 / (1.0 + np.exp(-steepness * (x - 0.5)))


CURVE_TYPES = {
    "Linear": linear_curve,
    "Gamma": lambda x: gamma_curve(x, 2.2),
    "S-Curve": lambda x: s_curve(x, 5.0),
    "Aggressive": lambda x: gamma_curve(x, 3.5),
    "Gentle": lambda x: gamma_curve(x, 1.5),
}


class PedalCalibration(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._update_curve()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Brake pedal response curve
        brake_group = QGroupBox("Brake Pedal Response Curve")
        bl = QVBoxLayout(brake_group)

        # Curve type selector
        row = QHBoxLayout()
        row.addWidget(QLabel("Curve Type:"))
        self._curve_combo = QComboBox()
        self._curve_combo.addItems(CURVE_TYPES.keys())
        self._curve_combo.currentTextChanged.connect(lambda: self._update_curve())
        row.addWidget(self._curve_combo)
        row.addStretch()
        bl.addLayout(row)

        # Gamma/steepness slider
        param_row = QHBoxLayout()
        param_row.addWidget(QLabel("Sensitivity:"))
        self._param_slider = QSlider(Qt.Horizontal)
        self._param_slider.setRange(10, 50)  # 1.0 to 5.0
        self._param_slider.setValue(22)
        self._param_label = QLabel("2.2")
        self._param_slider.valueChanged.connect(self._on_param_changed)
        param_row.addWidget(self._param_slider)
        param_row.addWidget(self._param_label)
        bl.addLayout(param_row)

        # Response curve plot
        self._plot = pg.PlotWidget(title="Input vs Output")
        self._plot.setLabel("left", "Output Force")
        self._plot.setLabel("bottom", "Pedal Travel")
        self._plot.setXRange(0, 1)
        self._plot.setYRange(0, 1)
        self._plot.setAspectLocked(True)

        # Reference line (linear)
        x_ref = np.linspace(0, 1, 100)
        self._plot.plot(x_ref, x_ref, pen=pg.mkPen("gray", width=1, style=Qt.DashLine))

        # Active curve
        self._curve_line = self._plot.plot(pen=pg.mkPen("lime", width=3))

        bl.addWidget(self._plot)
        layout.addWidget(brake_group)

        # Dead zone / max settings
        dz_group = QGroupBox("Dead Zones")
        dl = QVBoxLayout(dz_group)

        for pedal_name in ["Brake", "Throttle", "Clutch"]:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{pedal_name} Min:"))
            min_slider = QSlider(Qt.Horizontal)
            min_slider.setRange(0, 20)
            min_slider.setValue(2)
            row.addWidget(min_slider)
            row.addWidget(QLabel(f"Max:"))
            max_slider = QSlider(Qt.Horizontal)
            max_slider.setRange(80, 100)
            max_slider.setValue(100)
            row.addWidget(max_slider)
            dl.addLayout(row)

        layout.addWidget(dz_group)

        # Calibration wizard
        cal_group = QGroupBox("Calibration")
        cl = QHBoxLayout(cal_group)
        self._cal_btn = QPushButton("Start Calibration Wizard")
        self._cal_btn.setEnabled(False)  # Needs hardware
        cl.addWidget(self._cal_btn)
        cl.addWidget(QLabel("Press min/max on each pedal to set range"))
        cl.addStretch()
        layout.addWidget(cal_group)

    def _on_param_changed(self, value: int):
        param = value / 10.0
        self._param_label.setText(f"{param:.1f}")
        self._update_curve()

    def _update_curve(self):
        x = np.linspace(0, 1, 200)
        curve_name = self._curve_combo.currentText()
        param = self._param_slider.value() / 10.0

        if curve_name == "Linear":
            y = x.copy()
        elif curve_name == "Gamma" or curve_name == "Aggressive" or curve_name == "Gentle":
            y = np.power(x, param)
        elif curve_name == "S-Curve":
            raw = 1.0 / (1.0 + np.exp(-param * (x - 0.5)))
            y = (raw - raw[0]) / (raw[-1] - raw[0])  # Normalize to 0..1
        else:
            y = x.copy()

        self._curve_line.setData(x, y)

    def get_settings(self) -> dict:
        return {
            "curve_type": self._curve_combo.currentText(),
            "sensitivity": self._param_slider.value() / 10.0,
        }

    def apply_settings(self, settings: dict):
        if "curve_type" in settings:
            idx = self._curve_combo.findText(settings["curve_type"])
            if idx >= 0:
                self._curve_combo.setCurrentIndex(idx)
        if "sensitivity" in settings:
            self._param_slider.setValue(int(settings["sensitivity"] * 10))
