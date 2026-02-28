"""Main application window with tabbed interface."""
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QLabel, QHBoxLayout, QWidget,
)
from PySide6.QtCore import QTimer, Signal

from serial_comm import SerialComm
from controller_input import ControllerInput
from widgets.live_monitor import LiveMonitor
from widgets.ffb_settings import FFBSettings
from widgets.steering_settings import SteeringSettings
from widgets.safety_panel import SafetyPanel
from widgets.pedal_calibration import PedalCalibration
from widgets.profile_manager import ProfileManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFB Companion")
        self.setMinimumSize(900, 600)

        # --- Backend threads ---
        self.serial = SerialComm()
        self.controller = ControllerInput()

        # --- Tabs ---
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.live_monitor = LiveMonitor(self.serial)
        self.ffb_settings = FFBSettings(self.serial)
        self.steering_settings = SteeringSettings(self.serial)
        self.safety_panel = SafetyPanel(self.serial)
        self.pedal_calibration = PedalCalibration()
        self.profile_manager = ProfileManager(self)

        self.tabs.addTab(self.live_monitor, "Live Monitor")
        self.tabs.addTab(self.ffb_settings, "FFB Settings")
        self.tabs.addTab(self.steering_settings, "Steering")
        self.tabs.addTab(self.safety_panel, "Safety")
        self.tabs.addTab(self.pedal_calibration, "Pedals")
        self.tabs.addTab(self.profile_manager, "Profiles")

        # --- Status bar ---
        self.status_connection = QLabel("Disconnected")
        self.status_port = QLabel("")
        self.status_loop_rate = QLabel("")
        self.status_controller = QLabel("No controller")

        sb = self.statusBar()
        sb.addWidget(self.status_connection)
        sb.addWidget(self.status_port)
        sb.addWidget(self.status_loop_rate)
        sb.addPermanentWidget(self.status_controller)

        # --- Connections ---
        self.serial.connected.connect(self._on_serial_connected)
        self.serial.disconnected.connect(self._on_serial_disconnected)
        self.serial.telemetry_received.connect(self._on_telemetry)
        self.controller.steering_changed.connect(self._on_steering)
        self.controller.controller_status.connect(self._on_controller_status)

        # --- Start threads ---
        self.serial.start()
        self.controller.start()

    def _on_serial_connected(self, port: str):
        self.status_connection.setText("Connected")
        self.status_connection.setStyleSheet("color: green; font-weight: bold;")
        self.status_port.setText(f"({port})")

    def _on_serial_disconnected(self):
        self.status_connection.setText("Disconnected")
        self.status_connection.setStyleSheet("color: red;")
        self.status_port.setText("")
        self.status_loop_rate.setText("")

    def _on_telemetry(self, angle: int, loop_rate: int):
        self.status_loop_rate.setText(f"Loop: {loop_rate} Hz")

    def _on_steering(self, position: float):
        """Controller stick moved — send steering command to ESP32 and live monitor."""
        pos_int = int(position * 32767)
        self.serial.send_steering(pos_int)
        self.live_monitor.set_commanded(pos_int)

    def _on_controller_status(self, status: str):
        self.status_controller.setText(status)

    def get_all_settings(self) -> dict:
        """Collect settings from all widgets for profile save."""
        return {
            "ffb": self.ffb_settings.get_settings(),
            "steering": self.steering_settings.get_settings(),
            "safety": self.safety_panel.get_settings(),
            "pedals": self.pedal_calibration.get_settings(),
        }

    def apply_all_settings(self, settings: dict):
        """Apply loaded profile settings to all widgets."""
        if "ffb" in settings:
            self.ffb_settings.apply_settings(settings["ffb"])
        if "steering" in settings:
            self.steering_settings.apply_settings(settings["steering"])
        if "safety" in settings:
            self.safety_panel.apply_settings(settings["safety"])
        if "pedals" in settings:
            self.pedal_calibration.apply_settings(settings["pedals"])

    def closeEvent(self, event):
        self.serial.stop()
        self.controller.stop()
        event.accept()
