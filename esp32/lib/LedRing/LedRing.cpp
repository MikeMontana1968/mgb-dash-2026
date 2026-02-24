/**
 * MGB Dash 2026 — LED Ring Library Implementation
 *
 * Adafruit NeoPixel driver for WS2812B rings (12 pixels, GRB, 800 KHz).
 */

#include "LedRing.h"

void LedRing::init(int dataPin, int numLeds) {
    numLeds_ = numLeds;
    strip_ = new Adafruit_NeoPixel(numLeds, dataPin, NEO_GRB + NEO_KHZ800);
    strip_->begin();
    strip_->setBrightness(128);
    setAll(0, 0, 0);
    show();
}

void LedRing::setAll(uint8_t r, uint8_t g, uint8_t b) {
    uint32_t color = strip_->Color(r, g, b);
    for (int i = 0; i < numLeds_; i++) {
        strip_->setPixelColor(i, color);
    }
}

void LedRing::setPixel(int index, uint8_t r, uint8_t g, uint8_t b) {
    if (index >= 0 && index < numLeds_) {
        strip_->setPixelColor(index, strip_->Color(r, g, b));
    }
}

void LedRing::setAmbientLevel(uint8_t brightness) {
    ambientLevel_ = brightness;
}

void LedRing::setAmbientFromCategory(uint8_t category) {
    switch (category) {
        case AMBIENT_DAYLIGHT:       ambientLevel_ = 30;  break;
        case AMBIENT_EARLY_TWILIGHT: ambientLevel_ = 100; break;
        case AMBIENT_LATE_TWILIGHT:  ambientLevel_ = 180; break;
        case AMBIENT_DARKNESS:       ambientLevel_ = 255; break;
        default:                     ambientLevel_ = 128; break;
    }
}

void LedRing::startTurnSignal(bool left) {
    animating_ = true;
    hazardMode_ = false;
    turnLeft_ = left;
    animStep_ = 0;
    lastAnimStepMs_ = millis();
}

void LedRing::startHazard() {
    animating_ = true;
    hazardMode_ = true;
    animStep_ = 0;
    lastAnimStepMs_ = millis();
}

void LedRing::stopAnimation() {
    animating_ = false;
    hazardMode_ = false;
}

void LedRing::setWarning(uint8_t r, uint8_t g, uint8_t b) {
    warningActive_ = true;
    warnR_ = r;
    warnG_ = g;
    warnB_ = b;
}

void LedRing::clearWarning() {
    warningActive_ = false;
    warnR_ = 0;
    warnG_ = 0;
    warnB_ = 0;
}

void LedRing::runSelfTestChase() {
    // Sequential green chase: light each LED one at a time
    for (int i = 0; i < numLeds_; i++) {
        setAll(0, 0, 0);
        setPixel(i, 0, 255, 0);
        show();
        delay(40);
    }
    // Flash all green twice
    for (int f = 0; f < 2; f++) {
        setAll(0, 255, 0);
        show();
        delay(150);
        setAll(0, 0, 0);
        show();
        delay(150);
    }
    // Go dark
    setAll(0, 0, 0);
    show();
}

void LedRing::startBluePulse() {
    bluePulse_ = true;
    animating_ = false;
    warningActive_ = false;
}

void LedRing::stopBluePulse() {
    bluePulse_ = false;
}

bool LedRing::isBluePulsing() const {
    return bluePulse_;
}

void LedRing::update() {
    if (bluePulse_) {
        // Sine-wave blue breathing, ~2s period, brightness 20–255
        float phase = (float)(millis() % 2000) / 2000.0f * 2.0f * 3.14159265f;
        uint8_t brightness = (uint8_t)(137.5f + 117.5f * sinf(phase));
        setAll(0, 0, brightness);
    } else if (warningActive_) {
        setAll(warnR_, warnG_, warnB_);
    } else if (animating_) {
        // TODO: Implement turn signal sweep and hazard flash animations
        // For now, simple amber flash placeholder
        unsigned long now = millis();
        if (now - lastAnimStepMs_ > 100) {
            lastAnimStepMs_ = now;
            animStep_++;
            if (animStep_ % 2 == 0) {
                setAll(255, 165, 0);  // amber
            } else {
                setAll(0, 0, 0);
            }
        }
    } else {
        applyAmbient_();
    }
    show();
}

void LedRing::show() {
    strip_->show();
}

void LedRing::applyAmbient_() {
    setAll(ambientLevel_, ambientLevel_, ambientLevel_);
}
