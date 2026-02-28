"""Real-time telemetry graphs — servo position, commanded position."""
import collections
import time

import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import QTimer


HISTORY_LEN = 500  # ~10 seconds at 50Hz


class LiveMonitor(QWidget):
    def __init__(self, serial_comm, parent=None):
        super().__init__(parent)
        self._serial = serial_comm

        # Data buffers (ring buffers)
        self._times = collections.deque(maxlen=HISTORY_LEN)
        self._servo_angles = collections.deque(maxlen=HISTORY_LEN)
        self._commanded = collections.deque(maxlen=HISTORY_LEN)
        self._start_time = time.monotonic()
        self._last_commanded = 0

        self._setup_ui()

        # Connect telemetry signal
        self._serial.telemetry_received.connect(self._on_telemetry)

        # Refresh plot at 30fps
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_plot)
        self._timer.start(33)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Info labels
        info_row = QHBoxLayout()
        self._lbl_angle = QLabel("Servo Angle: --")
        self._lbl_commanded = QLabel("Commanded: --")
        self._lbl_rate = QLabel("Loop Rate: -- Hz")
        info_row.addWidget(self._lbl_angle)
        info_row.addWidget(self._lbl_commanded)
        info_row.addWidget(self._lbl_rate)
        info_row.addStretch()
        layout.addLayout(info_row)

        # Position plot
        self._plot_widget = pg.PlotWidget(title="Position")
        self._plot_widget.setLabel("left", "Value")
        self._plot_widget.setLabel("bottom", "Time", units="s")
        self._plot_widget.addLegend()
        self._plot_widget.setYRange(-35000, 35000)

        self._curve_servo = self._plot_widget.plot(
            pen=pg.mkPen("cyan", width=2), name="Servo Angle"
        )
        self._curve_commanded = self._plot_widget.plot(
            pen=pg.mkPen("yellow", width=2), name="Commanded"
        )

        layout.addWidget(self._plot_widget)

    def set_commanded(self, position: int):
        """Called externally to record what was sent to ESP32."""
        self._last_commanded = position

    def _on_telemetry(self, angle: int, loop_rate: int):
        t = time.monotonic() - self._start_time
        self._times.append(t)
        # Scale ADC 0-4095 to roughly match commanded range for visual comparison
        scaled_angle = int((angle / 4095.0) * 65535 - 32768)
        self._servo_angles.append(scaled_angle)
        self._commanded.append(self._last_commanded)

        self._lbl_angle.setText(f"Servo Angle: {angle}")
        self._lbl_commanded.setText(f"Commanded: {self._last_commanded}")
        self._lbl_rate.setText(f"Loop Rate: {loop_rate} Hz")

    def _update_plot(self):
        if len(self._times) < 2:
            return
        times = list(self._times)
        self._curve_servo.setData(times, list(self._servo_angles))
        self._curve_commanded.setData(times, list(self._commanded))
