/**
 * MGB Dash 2026 — LED Ring Library Implementation
 */

#include "LedRing.h"

void LedRing::init(int dataPin, int numLeds) {
    numLeds_ = numLeds;
    leds_ = new CRGB[numLeds];

    // FastLED.addLeds requires a compile-time pin, but we use a runtime
    // approach here. In practice, LED_DATA_PIN is a build-time constant.
    FastLED.addLeds<WS2812B, LED_DATA_PIN, GRB>(leds_, numLeds_);
    FastLED.setBrightness(128);
    setAll(CRGB::Black);
    show();
}

void LedRing::setAll(CRGB color) {
    for (int i = 0; i < numLeds_; i++) {
        leds_[i] = color;
    }
}

void LedRing::setPixel(int index, CRGB color) {
    if (index >= 0 && index < numLeds_) {
        leds_[index] = color;
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

void LedRing::setWarning(CRGB color) {
    warningActive_ = true;
    warningColor_ = color;
}

void LedRing::clearWarning() {
    warningActive_ = false;
    warningColor_ = CRGB::Black;
}

void LedRing::update() {
    if (warningActive_) {
        setAll(warningColor_);
    } else if (animating_) {
        // TODO: Implement turn signal sweep and hazard flash animations
        // For now, simple amber flash placeholder
        unsigned long now = millis();
        if (now - lastAnimStepMs_ > 100) {
            lastAnimStepMs_ = now;
            animStep_++;
            if (animStep_ % 2 == 0) {
                setAll(CRGB(255, 165, 0));  // amber
            } else {
                setAll(CRGB::Black);
            }
        }
    } else {
        applyAmbient_();
    }
    show();
}

void LedRing::show() {
    FastLED.show();
}

void LedRing::applyAmbient_() {
    CRGB white = CRGB(ambientLevel_, ambientLevel_, ambientLevel_);
    setAll(white);
}
