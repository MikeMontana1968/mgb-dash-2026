#pragma once
/**
 * MGB Dash 2026 — Servo Gauge Library
 *
 * Controls a 180-degree hobby servo for gauge needle positioning.
 * Maps input values to servo angles with configurable range and smoothing.
 */

#include <Arduino.h>
#include <ESP32Servo.h>

class ServoGauge {
public:
    /**
     * Initialize servo on specified pin.
     * @param pin  GPIO for servo PWM signal
     */
    void init(int pin);

    /**
     * Set input value range for mapping to 0–180 degrees.
     * @param minVal  Input value corresponding to 0 degrees
     * @param maxVal  Input value corresponding to 180 degrees
     */
    void setRange(float minVal, float maxVal);

    /**
     * Set servo angle directly (0–180 degrees).
     */
    void setAngle(int angle);

    /**
     * Map an input value to servo angle using configured range.
     * Value is clamped to [minVal, maxVal].
     */
    void setValue(float value);

    /** Blocking self-test: sweep 0→180→0 (~1.8s). Call from setup(). */
    void runSelfTestSweep();

    /**
     * Enable smoothing (exponential moving average).
     * @param factor  0.0 = no movement, 1.0 = instant (default 0.15)
     */
    void setSmoothing(float factor);

    /**
     * Call every loop iteration for smooth servo movement.
     * Applies smoothing filter and writes to servo.
     */
    void update();

    /** Get current angle (after smoothing). */
    int getCurrentAngle() const { return currentAngle_; }

private:
    Servo servo_;
    float minVal_ = 0.0f;
    float maxVal_ = 100.0f;
    int targetAngle_ = 0;
    int currentAngle_ = 0;
    float smoothingFactor_ = 0.15f;
    float smoothedAngle_ = 0.0f;
    bool initialized_ = false;
};
