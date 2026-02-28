#pragma once
#include <stdint.h>

// Packet format: [0xAA] [0x55] [CMD] [LEN] [PAYLOAD...] [CRC8]
#define PROTO_HEADER_0    0xAA
#define PROTO_HEADER_1    0x55
#define PROTO_MAX_PAYLOAD 16
#define PROTO_OVERHEAD     4  // header(2) + cmd(1) + len(1) + crc(1) = 5, but len excludes itself

// Commands: PC → ESP32
#define CMD_SET_STEERING  0x01  // int16_t position (-32768 to 32767)
#define CMD_SET_GAIN      0x02  // uint8_t gain (0-100)
#define CMD_SET_ENABLE    0x03  // uint8_t enable (0=disable, 1=enable)

// Commands: ESP32 → PC
#define CMD_TELEMETRY     0x10  // int16_t angle + uint16_t loop_rate_hz
#define CMD_FAULT         0x11  // uint8_t fault_code

// Commands: Bidirectional
#define CMD_HEARTBEAT     0xF0  // No payload

// Fault codes
#define FAULT_NONE            0x00
#define FAULT_SERIAL_TIMEOUT  0x01
#define FAULT_SERVO_ERROR     0x02
#define FAULT_ADC_ERROR       0x03

// CRC-8 (polynomial 0x07)
static inline uint8_t crc8(const uint8_t *data, uint8_t len) {
    uint8_t crc = 0x00;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t j = 0; j < 8; j++) {
            crc = (crc & 0x80) ? (crc << 1) ^ 0x07 : (crc << 1);
        }
    }
    return crc;
}

// Packet structure for parsing
typedef struct {
    uint8_t cmd;
    uint8_t len;
    uint8_t payload[PROTO_MAX_PAYLOAD];
} Packet;
