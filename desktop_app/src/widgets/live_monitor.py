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

        # Separate time+data buffers for each source
        self._cmd_times = collections.deque(maxlen=HISTORY_LEN)
        self._commanded = collections.deque(maxlen=HISTORY_LEN)
        self._servo_times = collections.deque(maxlen=HISTORY_LEN)
        self._servo_angles = collections.deque(maxlen=HISTORY_LEN)
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
        """Called externally when controller input changes."""
        self._last_commanded = position
        self._lbl_commanded.setText(f"Commanded: {position}")
        # Always record commanded position so the graph works without ESP32
        t = time.monotonic() - self._start_time
        self._cmd_times.append(t)
        self._commanded.append(position)

    def _on_telemetry(self, angle: int, loop_rate: int):
        t = time.monotonic() - self._start_time
        # Scale ADC 0-4095 to roughly match commanded range for visual comparison
        scaled_angle = int((angle / 4095.0) * 65535 - 32768)
        self._servo_times.append(t)
        self._servo_angles.append(scaled_angle)

        self._lbl_angle.setText(f"Servo Angle: {angle}")
        self._lbl_rate.setText(f"Loop Rate: {loop_rate} Hz")

    def _update_plot(self):
        if len(self._cmd_times) >= 2:
            self._curve_commanded.setData(list(self._cmd_times), list(self._commanded))
        if len(self._servo_times) >= 2:
            self._curve_servo.setData(list(self._servo_times), list(self._servo_angles))
