"""Pedal calibration — per-pedal response curve editor with shared graph."""
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QComboBox, QSlider, QGridLayout,
)
from PySide6.QtCore import Qt

CURVE_TYPES = ["Linear", "Gamma", "S-Curve"]

PEDALS = [
    {"name": "Brake",    "color": "red",   "default_curve": "Gamma",   "default_sens": 22},
    {"name": "Throttle", "color": "lime",  "default_curve": "Linear",  "default_sens": 10},
    {"name": "Clutch",   "color": "cyan",  "default_curve": "Linear",  "default_sens": 10},
]


def _compute_curve(x: np.ndarray, curve_type: str, sensitivity: float) -> np.ndarray:
    if curve_type == "Linear":
        return x.copy()
    elif curve_type == "Gamma":
        return np.power(x, sensitivity)
    elif curve_type == "S-Curve":
        raw = 1.0 / (1.0 + np.exp(-sensitivity * (x - 0.5)))
        return (raw - raw[0]) / (raw[-1] - raw[0])
    return x.copy()


class _PedalControls:
    """UI controls for a single pedal axis."""

    def __init__(self, pedal_info: dict, on_changed):
        self.name = pedal_info["name"]
        self.color = pedal_info["color"]
        self._on_changed = on_changed

        self.curve_combo = QComboBox()
        self.curve_combo.addItems(CURVE_TYPES)
        idx = CURVE_TYPES.index(pedal_info["default_curve"])
        self.curve_combo.setCurrentIndex(idx)
        self.curve_combo.currentTextChanged.connect(lambda: self._on_changed())

        self.sens_slider = QSlider(Qt.Horizontal)
        self.sens_slider.setRange(10, 50)  # 1.0 to 5.0
        self.sens_slider.setValue(pedal_info["default_sens"])
        self.sens_label = QLabel(f"{pedal_info['default_sens'] / 10.0:.1f}")
        self.sens_slider.valueChanged.connect(self._on_sens)

        self.dz_min_slider = QSlider(Qt.Horizontal)
        self.dz_min_slider.setRange(0, 20)
        self.dz_min_slider.setValue(2)
        self.dz_min_label = QLabel("2%")
        self.dz_min_slider.valueChanged.connect(
            lambda v: self.dz_min_label.setText(f"{v}%")
        )

        self.dz_max_slider = QSlider(Qt.Horizontal)
        self.dz_max_slider.setRange(80, 100)
        self.dz_max_slider.setValue(100)
        self.dz_max_label = QLabel("100%")
        self.dz_max_slider.valueChanged.connect(
            lambda v: self.dz_max_label.setText(f"{v}%")
        )

    def _on_sens(self, value: int):
        self.sens_label.setText(f"{value / 10.0:.1f}")
        self._on_changed()

    @property
    def curve_type(self) -> str:
        return self.curve_combo.currentText()

    @property
    def sensitivity(self) -> float:
        return self.sens_slider.value() / 10.0

    def get_settings(self) -> dict:
        return {
            "curve_type": self.curve_type,
            "sensitivity": self.sensitivity,
            "deadzone_min": self.dz_min_slider.value(),
            "deadzone_max": self.dz_max_slider.value(),
        }

    def apply_settings(self, s: dict):
        if "curve_type" in s:
            idx = self.curve_combo.findText(s["curve_type"])
            if idx >= 0:
                self.curve_combo.setCurrentIndex(idx)
        if "sensitivity" in s:
            self.sens_slider.setValue(int(s["sensitivity"] * 10))
        if "deadzone_min" in s:
            self.dz_min_slider.setValue(s["deadzone_min"])
        if "deadzone_max" in s:
            self.dz_max_slider.setValue(s["deadzone_max"])


class PedalCalibration(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pedals: dict[str, _PedalControls] = {}
        self._curves: dict[str, pg.PlotDataItem] = {}
        self._setup_ui()
        self._update_curves()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # --- Response curve graph (shared, locked) ---
        self._plot = pg.PlotWidget(title="Pedal Response Curves")
        self._plot.setLabel("left", "Output Force")
        self._plot.setLabel("bottom", "Pedal Travel")
        self._plot.setXRange(0, 1, padding=0)
        self._plot.setYRange(0, 1, padding=0)
        self._plot.setLimits(xMin=0, xMax=1, yMin=0, yMax=1)
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.setMenuEnabled(False)
        self._plot.addLegend()

        # Reference line (linear, dashed gray)
        x_ref = np.linspace(0, 1, 100)
        self._plot.plot(x_ref, x_ref, pen=pg.mkPen("gray", width=1, style=Qt.DashLine))

        # Create a curve line per pedal
        for pedal_info in PEDALS:
            name = pedal_info["name"]
            curve = self._plot.plot(
                pen=pg.mkPen(pedal_info["color"], width=3), name=name
            )
            self._curves[name] = curve

        layout.addWidget(self._plot)

        # --- Per-pedal controls ---
        for pedal_info in PEDALS:
            name = pedal_info["name"]
            pc = _PedalControls(pedal_info, self._update_curves)
            self._pedals[name] = pc

            group = QGroupBox(f"{name}  ({pedal_info['color']})")
            grid = QGridLayout(group)

            grid.addWidget(QLabel("Curve:"), 0, 0)
            grid.addWidget(pc.curve_combo, 0, 1, 1, 2)

            grid.addWidget(QLabel("Sensitivity:"), 1, 0)
            grid.addWidget(pc.sens_slider, 1, 1)
            grid.addWidget(pc.sens_label, 1, 2)

            grid.addWidget(QLabel("Dead Zone Min:"), 2, 0)
            grid.addWidget(pc.dz_min_slider, 2, 1)
            grid.addWidget(pc.dz_min_label, 2, 2)

            grid.addWidget(QLabel("Dead Zone Max:"), 3, 0)
            grid.addWidget(pc.dz_max_slider, 3, 1)
            grid.addWidget(pc.dz_max_label, 3, 2)

            layout.addWidget(group)

        # --- Calibration wizard ---
        cal_group = QGroupBox("Calibration")
        cl = QHBoxLayout(cal_group)
        self._cal_btn = QPushButton("Start Calibration Wizard")
        self._cal_btn.setEnabled(False)  # Needs hardware
        cl.addWidget(self._cal_btn)
        cl.addWidget(QLabel("Press min/max on each pedal to set range"))
        cl.addStretch()
        layout.addWidget(cal_group)

    def _update_curves(self):
        x = np.linspace(0, 1, 200)
        for name, pc in self._pedals.items():
            y = _compute_curve(x, pc.curve_type, pc.sensitivity)
            self._curves[name].setData(x, y)

    def get_settings(self) -> dict:
        return {name: pc.get_settings() for name, pc in self._pedals.items()}

    def apply_settings(self, settings: dict):
        for name, s in settings.items():
            if name in self._pedals:
                self._pedals[name].apply_settings(s)
        self._update_curves()
