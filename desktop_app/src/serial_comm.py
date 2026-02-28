"""Serial communication thread — auto-detect ESP32, send/receive packets."""
import time
import serial
import serial.tools.list_ports
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from protocol import (
    decode_packet, set_steering, set_gain, set_enable, heartbeat,
    parse_telemetry, parse_fault,
    CMD_TELEMETRY, CMD_FAULT, CMD_HEARTBEAT,
)

# ESP32-S3 USB VID/PID
ESP32_VID = 0x303A
ESP32_PID = 0x1001


class SerialComm(QThread):
    connected = Signal(str)       # port name
    disconnected = Signal()
    telemetry_received = Signal(int, int)   # angle, loop_rate
    fault_received = Signal(int, str)       # code, name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._port: serial.Serial | None = None
        self._mutex = QMutex()
        self._tx_queue: list[bytes] = []

    def stop(self):
        self._running = False
        self.wait(2000)

    def send_steering(self, position: int):
        with QMutexLocker(self._mutex):
            self._tx_queue.append(set_steering(position))

    def send_gain(self, gain: int):
        with QMutexLocker(self._mutex):
            self._tx_queue.append(set_gain(gain))

    def send_enable(self, enable: bool):
        with QMutexLocker(self._mutex):
            self._tx_queue.append(set_enable(enable))

    def _find_esp32(self) -> str | None:
        for port in serial.tools.list_ports.comports():
            if port.vid == ESP32_VID and port.pid == ESP32_PID:
                return port.device
        return None

    def _connect(self) -> bool:
        port_name = self._find_esp32()
        if not port_name:
            return False
        try:
            self._port = serial.Serial(port_name, 115200, timeout=0.05)
            self.connected.emit(port_name)
            return True
        except serial.SerialException:
            self._port = None
            return False

    def _disconnect(self):
        if self._port and self._port.is_open:
            try:
                self._port.close()
            except Exception:
                pass
        self._port = None
        self.disconnected.emit()

    def run(self):
        self._running = True
        rx_buf = bytearray()
        last_heartbeat = 0.0

        while self._running:
            # --- Connect if needed ---
            if self._port is None or not self._port.is_open:
                if not self._connect():
                    time.sleep(1.0)  # Retry scan every second
                    continue

            try:
                # --- TX: send queued packets ---
                with QMutexLocker(self._mutex):
                    to_send = list(self._tx_queue)
                    self._tx_queue.clear()
                for pkt in to_send:
                    self._port.write(pkt)

                # --- Heartbeat ---
                now = time.monotonic()
                if now - last_heartbeat > 0.5:
                    self._port.write(heartbeat())
                    last_heartbeat = now

                # --- RX: read and parse ---
                data = self._port.read(256)
                if data:
                    rx_buf.extend(data)

                while True:
                    pkt, consumed = decode_packet(rx_buf)
                    if consumed > 0:
                        rx_buf = rx_buf[consumed:]
                    if pkt is None:
                        break
                    self._handle_packet(pkt)

            except serial.SerialException:
                self._disconnect()
                time.sleep(0.5)

    def _handle_packet(self, pkt: dict):
        cmd = pkt["cmd"]
        payload = pkt["payload"]

        if cmd == CMD_TELEMETRY and len(payload) >= 4:
            t = parse_telemetry(payload)
            self.telemetry_received.emit(t["angle"], t["loop_rate"])
        elif cmd == CMD_FAULT and len(payload) >= 1:
            f = parse_fault(payload)
            self.fault_received.emit(f["code"], f["name"])
