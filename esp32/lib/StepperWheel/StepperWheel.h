#pragma once
/**
 * MGB Dash 2026 — Stepper Wheel Library
 *
 * Controls a 28BYJ-48 stepper motor (via ULN2003 driver) for a mechanical
 * speedometer needle.  Optical endstop sensor provides home calibration.
 *
 * Ported from prototype SpeedometerWheel — all hardcoded GPIO references
 * removed; pins are passed via init().
 *
 * Key features:
 *   - Home calibration (find optical marker, center on it)
 *   - Cubic-eased transitions (1200 ms, smooth start/stop)
 *   - Shortest-path rotation (wraps around full revolution)
 *   - MPH → step-position mapping with configurable zero offset
 */

#include <Arduino.h>
#include <Stepper.h>
#include <cmath>

class StepperWheel {
public:
    // ── Constants ──────────────────────────────────────────────────────
    static constexpr int STEPS_PER_REVOLUTION = 2048;
    static constexpr int STEPPER_RPM          = 15;
    static constexpr int MAX_SPEED_MPH        = 90;
    static constexpr int MIN_SPEED_MPH        = 0;
    static constexpr int SPEED_RANGE          = MAX_SPEED_MPH - MIN_SPEED_MPH;
    static constexpr int STEPS_PER_MPH        = STEPS_PER_REVOLUTION / SPEED_RANGE;
    static constexpr int ZERO_MPH_OFFSET      = 256;   // steps from home to 0 MPH
    static constexpr unsigned long TRANSITION_TIME_MS = 1200;

    /**
     * Initialize stepper and endstop.
     * Pin order follows 28BYJ-48 convention: IN1, IN3, IN2, IN4 passed to
     * Arduino Stepper library for correct full-step sequence.
     *
     * @param in1         GPIO for ULN2003 IN1
     * @param in2         GPIO for ULN2003 IN2
     * @param in3         GPIO for ULN2003 IN3
     * @param in4         GPIO for ULN2003 IN4
     * @param endstopPin  GPIO for optical home sensor (active-HIGH when marker detected)
     */
    void init(int in1, int in2, int in3, int in4, int endstopPin);

    /**
     * Home calibration — rotate until optical marker is found, center on it.
     * Blocking; takes a few seconds.
     * @return true if home was found successfully
     */
    bool calibrateHome();

    /**
     * Begin a smooth eased transition to the given speed.
     * @param mph  Target speed (clamped to 0–90)
     */
    void moveToMPH(int mph);

    /**
     * Drive eased needle movement.  Call every loop iteration.
     */
    void update();

    // ── Getters ────────────────────────────────────────────────────────
    int  getCurrentMPH()  const;
    bool isCalibrated()   const { return calibrated_; }
    bool isInTransition() const { return moving_; }

    // ── Test / debug helpers ───────────────────────────────────────────
    void testStepperMotor();
    void manualStepperTest();

private:
    Stepper* stepper_ = nullptr;
    int endstopPin_ = -1;
    int in1_ = -1, in2_ = -1, in3_ = -1, in4_ = -1;

    // Position tracking
    int   currentPosition_   = 0;
    int   targetPosition_    = 0;
    float currentPosF_       = 0.0f;
    float startPosF_         = 0.0f;
    float targetPosF_        = 0.0f;

    // Calibration state
    int  homeStartPos_   = 0;
    int  homeEndPos_     = 0;
    int  homeMarkerWidth_= 0;
    bool calibrated_     = false;

    // Transition state
    bool          moving_          = false;
    unsigned long transitionStart_ = 0;

    // Helpers
    bool  readEndstop();
    void  singleStep(bool clockwise);
    int   findEdge(bool clockwise, bool risingEdge);
    float easeInOutCubic(float t);
    void  updateStepperPosition();
    int   shortestPath(int from, int to);
    int   stepsFromHome(int mph);
};
