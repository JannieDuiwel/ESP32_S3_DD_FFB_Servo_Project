"""Serial protocol encode/decode — mirrors firmware/include/protocol.h"""
import struct

HEADER = bytes([0xAA, 0x55])

# Commands: PC -> ESP32
CMD_SET_STEERING = 0x01
CMD_SET_GAIN     = 0x02
CMD_SET_ENABLE   = 0x03

# Commands: ESP32 -> PC
CMD_TELEMETRY    = 0x10
CMD_FAULT        = 0x11

# Bidirectional
CMD_HEARTBEAT    = 0xF0

# Fault codes
FAULT_NONE           = 0x00
FAULT_SERIAL_TIMEOUT = 0x01
FAULT_SERVO_ERROR    = 0x02
FAULT_ADC_ERROR      = 0x03

FAULT_NAMES = {
    FAULT_NONE: "None",
    FAULT_SERIAL_TIMEOUT: "Serial Timeout",
    FAULT_SERVO_ERROR: "Servo Error",
    FAULT_ADC_ERROR: "ADC Error",
}


def _crc8(data: bytes) -> int:
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) if (crc & 0x80) else (crc << 1)
            crc &= 0xFF
    return crc


def encode_packet(cmd: int, payload: bytes = b"") -> bytes:
    pkt = bytes([cmd, len(payload)]) + payload
    return HEADER + pkt + bytes([_crc8(pkt)])


def decode_packet(buf: bytearray) -> tuple[dict | None, int]:
    """Try to decode one packet from buffer.

    Returns (packet_dict, bytes_consumed).
    packet_dict is None if no complete valid packet found.
    """
    while len(buf) >= 5:  # minimum packet: header(2) + cmd(1) + len(1) + crc(1)
        # Find header
        idx = buf.find(HEADER)
        if idx < 0:
            return None, max(len(buf) - 1, 0)
        if idx > 0:
            return None, idx  # skip garbage bytes before header

        if len(buf) < idx + 4:
            return None, 0  # need more data

        cmd = buf[idx + 2]
        plen = buf[idx + 3]
        total = 5 + plen  # header(2) + cmd(1) + len(1) + payload(plen) + crc(1)

        if len(buf) < idx + total:
            return None, 0  # need more data

        pkt_data = buf[idx + 2 : idx + 4 + plen]  # cmd + len + payload
        expected_crc = _crc8(pkt_data)
        actual_crc = buf[idx + 4 + plen]

        if expected_crc != actual_crc:
            return None, idx + 2  # bad crc, skip past this header

        payload = bytes(buf[idx + 4 : idx + 4 + plen])
        return {"cmd": cmd, "payload": payload}, idx + total

    return None, 0


# Convenience encoders
def set_steering(position: int) -> bytes:
    """position: -32768 to 32767"""
    return encode_packet(CMD_SET_STEERING, struct.pack("<h", max(-32768, min(32767, position))))

def set_gain(gain: int) -> bytes:
    """gain: 0-100"""
    return encode_packet(CMD_SET_GAIN, struct.pack("B", max(0, min(100, gain))))

def set_enable(enable: bool) -> bytes:
    return encode_packet(CMD_SET_ENABLE, struct.pack("B", 1 if enable else 0))

def heartbeat() -> bytes:
    return encode_packet(CMD_HEARTBEAT)


# Convenience decoders
def parse_telemetry(payload: bytes) -> dict:
    angle, loop_rate = struct.unpack("<hH", payload[:4])
    return {"angle": angle, "loop_rate": loop_rate}

def parse_fault(payload: bytes) -> dict:
    code = payload[0]
    return {"code": code, "name": FAULT_NAMES.get(code, f"Unknown(0x{code:02X})")}
