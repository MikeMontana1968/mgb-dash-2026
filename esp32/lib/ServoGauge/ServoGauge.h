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

    /** Write angle directly, bypassing smoothing. For coordinated self-test. */
    void writeDirect(int angle);

    /**
     * Set needle damping time constant in seconds.
     * The needle reaches ~63% of a new value in one time constant,
     * ~95% in three time constants.  Default 0.4s (~1.2s to settle).
     * @param seconds  Time constant (0.05–5.0).  Lower = snappier.
     */
    void setSmoothing(float seconds);

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
    float smoothingTau_ = 0.4f;       // time constant in seconds
    float smoothedAngle_ = 0.0f;
    unsigned long lastUpdateMs_ = 0;
    bool initialized_ = false;
};
