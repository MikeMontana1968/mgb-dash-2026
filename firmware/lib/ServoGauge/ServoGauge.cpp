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
    lastUpdateMs_ = millis();
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

void ServoGauge::runSelfTestSweep() {
    if (!initialized_) return;
    // Sweep 0 → 180 in 2-degree steps (10ms each = ~900ms)
    for (int a = 0; a <= 180; a += 2) {
        servo_.write(a);
        delay(10);
    }
    // Sweep 180 → 0
    for (int a = 180; a >= 0; a -= 2) {
        servo_.write(a);
        delay(10);
    }
    // Reset smoothing state
    smoothedAngle_ = 0.0f;
    targetAngle_ = 0;
    currentAngle_ = 0;
    servo_.write(0);
}

void ServoGauge::writeDirect(int angle) {
    if (!initialized_) return;
    angle = constrain(angle, 0, 180);
    servo_.write(angle);
    currentAngle_ = angle;
    targetAngle_ = angle;
    smoothedAngle_ = (float)angle;
    lastUpdateMs_ = millis();
}

void ServoGauge::setSmoothing(float seconds) {
    smoothingTau_ = constrain(seconds, 0.05f, 5.0f);
}

void ServoGauge::update() {
    if (!initialized_) return;

    unsigned long now = millis();
    float dt = (now - lastUpdateMs_) / 1000.0f;
    lastUpdateMs_ = now;

    // Clamp dt to avoid jumps after long pauses (e.g. self-test)
    if (dt > 0.5f) dt = 0.5f;

    // Time-based EMA: consistent damping regardless of loop speed.
    // alpha approaches 1.0 for large dt, 0.0 for small dt.
    float alpha = 1.0f - expf(-dt / smoothingTau_);
    smoothedAngle_ += alpha * ((float)targetAngle_ - smoothedAngle_);

    currentAngle_ = (int)(smoothedAngle_ + 0.5f);
    currentAngle_ = constrain(currentAngle_, 0, 180);

    servo_.write(currentAngle_);
}
