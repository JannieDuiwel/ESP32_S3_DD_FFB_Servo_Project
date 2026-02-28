#pragma once

// --- Servo PWM ---
#define SERVO_PIN           4
#define SERVO_FREQ_HZ       50
#define SERVO_MIN_US        500
#define SERVO_MAX_US        2500
#define SERVO_CENTER_US     1500

// --- Servo angle feedback (ADC) ---
#define SERVO_ADC_PIN       5

// --- Timing ---
#define CONTROL_LOOP_HZ     50    // Hobby servo can't handle 1kHz, 50Hz is fine
#define SERIAL_TIMEOUT_MS   1000  // Disable servo after 1s of no commands
#define TELEMETRY_INTERVAL_MS 20  // Send telemetry at 50Hz
#define HEARTBEAT_INTERVAL_MS 500

// --- Safety ---
#define DEFAULT_GAIN        50    // 0-100
