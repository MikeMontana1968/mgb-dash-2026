#pragma once
/**
 * MGB Dash 2026 — WS2812B LED Ring Library
 *
 * Drives 12-pixel LED ring for gauge backlighting, turn signals,
 * warning colors, and ambient light blending.
 *
 * Uses Adafruit NeoPixel library (NEO_GRB, 800 KHz).
 */

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "can_ids.h"

class LedRing {
public:
    /**
     * Initialize LED ring.
     * @param dataPin  GPIO for WS2812B data line
     * @param numLeds  Number of LEDs in the ring
     */
    void init(int dataPin, int numLeds);

    /** Set all LEDs to a single color. */
    void setAll(uint8_t r, uint8_t g, uint8_t b);

    /** Set a single LED. */
    void setPixel(int index, uint8_t r, uint8_t g, uint8_t b);

    /** Set ambient white backlight level (0–255). Blended with other effects. */
    void setAmbientLevel(uint8_t brightness);

    /**
     * Update ambient level from ambient light category.
     * DAYLIGHT=low, DARKNESS=high white backlight.
     */
    void setAmbientFromCategory(uint8_t category);

    /** Start turn signal animation (left or right sweep). */
    void startTurnSignal(bool left);

    /** Start hazard animation (all LEDs flash amber). */
    void startHazard();

    /** Stop turn/hazard animation. */
    void stopAnimation();

    /** Set warning color (overrides ambient, e.g., bright red for alerts). */
    void setWarning(uint8_t r, uint8_t g, uint8_t b);

    /** Clear warning, return to ambient. */
    void clearWarning();

    /** Blocking self-test: green chase around ring (~1.5s). Call from setup(). */
    void runSelfTestChase();

    /** Start blue breathing fault animation (CAN silence). */
    void startBluePulse();

    /** Stop blue breathing fault animation. */
    void stopBluePulse();

    /** True if blue pulse fault mode is active. */
    bool isBluePulsing() const;

    /**
     * Call every loop iteration. Drives animations and pushes to LEDs.
     * Must be called frequently for smooth animations.
     */
    void update();

    /** Show the current LED state (push to hardware). */
    void show();

private:
    Adafruit_NeoPixel* strip_ = nullptr;
    int numLeds_ = 0;
    uint8_t ambientLevel_ = 128;
    bool animating_ = false;
    bool hazardMode_ = false;
    bool turnLeft_ = false;
    bool warningActive_ = false;
    bool bluePulse_ = false;
    uint8_t warnR_ = 0, warnG_ = 0, warnB_ = 0;
    unsigned long lastAnimStepMs_ = 0;
    int animStep_ = 0;

    void applyAmbient_();
};
