#include <Arduino.h>
#include "config.h"
#include "protocol.h"

// --- State ---
static bool     servo_enabled = false;
static int16_t  commanded_pos = 0;    // -32768 to 32767 from PC
static uint8_t  gain = DEFAULT_GAIN;
static int16_t  servo_angle_adc = 0;  // Raw ADC reading from angle wire
static uint16_t loop_rate_hz = 0;
static uint8_t  fault_code = FAULT_NONE;

static uint32_t last_cmd_time = 0;
static uint32_t last_telemetry_time = 0;
static uint32_t last_heartbeat_time = 0;
static uint32_t loop_count = 0;
static uint32_t loop_rate_timer = 0;

// --- Serial RX buffer ---
static uint8_t  rx_buf[64];
static uint8_t  rx_pos = 0;

// --- Servo PWM via LEDC ---
static const uint8_t LEDC_CHANNEL = 0;
static const uint8_t LEDC_RESOLUTION = 16;  // 16-bit for fine control

static uint32_t microsToTicks(uint32_t us) {
    // At 50Hz with 16-bit resolution: 1 tick = 1000000 / (50 * 65536) ≈ 0.305us
    return (uint32_t)((uint64_t)us * (1 << LEDC_RESOLUTION) * SERVO_FREQ_HZ / 1000000UL);
}

static void servoWriteUs(uint32_t us) {
    us = constrain(us, SERVO_MIN_US, SERVO_MAX_US);
    ledcWrite(LEDC_CHANNEL, microsToTicks(us));
}

static void servoDisable() {
    ledcWrite(LEDC_CHANNEL, 0);  // No pulses = servo relaxed
}

// Map commanded position (-32768..32767) to servo pulse width
static uint32_t positionToUs(int16_t pos) {
    // Apply gain: scale the deflection from center
    int32_t deflection = (int32_t)pos * gain / 100;
    // Map -32768..32767 → SERVO_MIN_US..SERVO_MAX_US
    uint32_t us = (uint32_t)map(deflection, -32768, 32767, SERVO_MIN_US, SERVO_MAX_US);
    return us;
}

// --- Protocol handling ---
static void handlePacket(uint8_t cmd, const uint8_t *payload, uint8_t len) {
    last_cmd_time = millis();

    switch (cmd) {
        case CMD_SET_STEERING:
            if (len >= 2) {
                commanded_pos = (int16_t)(payload[0] | (payload[1] << 8));
            }
            break;
        case CMD_SET_GAIN:
            if (len >= 1) {
                gain = min(payload[0], (uint8_t)100);
            }
            break;
        case CMD_SET_ENABLE:
            if (len >= 1) {
                servo_enabled = payload[0] != 0;
                if (!servo_enabled) {
                    servoDisable();
                }
            }
            break;
        case CMD_HEARTBEAT:
            break;  // Just resets timeout via last_cmd_time
        default:
            break;
    }
}

static void processSerial() {
    while (Serial.available()) {
        if (rx_pos >= sizeof(rx_buf)) {
            rx_pos = 0;  // Overflow protection
        }
        rx_buf[rx_pos++] = Serial.read();
    }

    // Try to parse packets from buffer
    uint8_t search = 0;
    while (search + 4 < rx_pos) {
        // Find header
        if (rx_buf[search] != PROTO_HEADER_0 || rx_buf[search + 1] != PROTO_HEADER_1) {
            search++;
            continue;
        }

        uint8_t cmd = rx_buf[search + 2];
        uint8_t plen = rx_buf[search + 3];
        uint8_t total = 5 + plen;  // header(2) + cmd(1) + len(1) + payload + crc(1)

        if (search + total > rx_pos) {
            break;  // Need more data
        }

        // Verify CRC over cmd + len + payload
        uint8_t crc_data_len = 2 + plen;
        uint8_t expected = crc8(&rx_buf[search + 2], crc_data_len);
        uint8_t actual = rx_buf[search + 4 + plen];

        if (expected == actual) {
            handlePacket(cmd, &rx_buf[search + 4], plen);
        }

        search += total;
    }

    // Shift remaining data to front
    if (search > 0) {
        uint8_t remaining = rx_pos - search;
        memmove(rx_buf, &rx_buf[search], remaining);
        rx_pos = remaining;
    }
}

static void sendPacket(uint8_t cmd, const uint8_t *payload, uint8_t len) {
    uint8_t pkt[5 + PROTO_MAX_PAYLOAD];
    pkt[0] = PROTO_HEADER_0;
    pkt[1] = PROTO_HEADER_1;
    pkt[2] = cmd;
    pkt[3] = len;
    if (len > 0) {
        memcpy(&pkt[4], payload, len);
    }
    pkt[4 + len] = crc8(&pkt[2], 2 + len);
    Serial.write(pkt, 5 + len);
}

static void sendTelemetry() {
    uint8_t payload[4];
    payload[0] = servo_angle_adc & 0xFF;
    payload[1] = (servo_angle_adc >> 8) & 0xFF;
    payload[2] = loop_rate_hz & 0xFF;
    payload[3] = (loop_rate_hz >> 8) & 0xFF;
    sendPacket(CMD_TELEMETRY, payload, 4);
}

static void sendFault(uint8_t code) {
    sendPacket(CMD_FAULT, &code, 1);
}

// ============================================================
void setup() {
    Serial.begin(115200);

    // Configure LEDC for servo PWM
    ledcSetup(LEDC_CHANNEL, SERVO_FREQ_HZ, LEDC_RESOLUTION);
    ledcAttachPin(SERVO_PIN, LEDC_CHANNEL);
    servoDisable();

    // ADC for angle feedback
    analogReadResolution(12);
    pinMode(SERVO_ADC_PIN, INPUT);

    last_cmd_time = millis();
    loop_rate_timer = millis();

    // Brief delay for serial to initialize
    delay(100);
}

void loop() {
    uint32_t now = millis();

    // --- Process incoming serial ---
    processSerial();

    // --- Safety: serial timeout ---
    if (servo_enabled && (now - last_cmd_time > SERIAL_TIMEOUT_MS)) {
        servo_enabled = false;
        servoDisable();
        fault_code = FAULT_SERIAL_TIMEOUT;
        sendFault(fault_code);
    }

    // --- Read angle feedback ---
    servo_angle_adc = analogRead(SERVO_ADC_PIN);

    // --- Drive servo ---
    if (servo_enabled) {
        servoWriteUs(positionToUs(commanded_pos));
    }

    // --- Send telemetry ---
    if (now - last_telemetry_time >= TELEMETRY_INTERVAL_MS) {
        last_telemetry_time = now;
        sendTelemetry();
    }

    // --- Heartbeat ---
    if (now - last_heartbeat_time >= HEARTBEAT_INTERVAL_MS) {
        last_heartbeat_time = now;
        sendPacket(CMD_HEARTBEAT, nullptr, 0);
    }

    // --- Loop rate measurement ---
    loop_count++;
    if (now - loop_rate_timer >= 1000) {
        loop_rate_hz = loop_count;
        loop_count = 0;
        loop_rate_timer = now;
    }

    // --- Pace the loop ---
    uint32_t loop_period_ms = 1000 / CONTROL_LOOP_HZ;
    uint32_t elapsed = millis() - now;
    if (elapsed < loop_period_ms) {
        delay(loop_period_ms - elapsed);
    }
}
