/**
 * MGB Dash 2026 — Servo Gauge Library Implementation
 */

#include "ServoGauge.h"

void ServoGauge::init(int pin) {
    servo_.attach(pin);
    servo_.write(0);
    currentAngle_ = 0;
    targetAngle_ = 0;
    smoothedAngle_ = 0.0f;
    initialized_ = true;
}

void ServoGauge::setRange(float minVal, float maxVal) {
    minVal_ = minVal;
    maxVal_ = maxVal;
}

void ServoGauge::setAngle(int angle) {
    targetAngle_ = constrain(angle, 0, 180);
}

void ServoGauge::setValue(float value) {
    float clamped = constrain(value, minVal_, maxVal_);
    float normalized = (clamped - minVal_) / (maxVal_ - minVal_);
    targetAngle_ = (int)(normalized * 180.0f);
}

void ServoGauge::setSmoothing(float factor) {
    smoothingFactor_ = constrain(factor, 0.01f, 1.0f);
}

void ServoGauge::update() {
    if (!initialized_) return;

    // Exponential moving average for smooth needle movement
    smoothedAngle_ += smoothingFactor_ * ((float)targetAngle_ - smoothedAngle_);
    currentAngle_ = (int)(smoothedAngle_ + 0.5f);
    currentAngle_ = constrain(currentAngle_, 0, 180);

    servo_.write(currentAngle_);
}
