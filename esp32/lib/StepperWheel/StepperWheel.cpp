/**
 * MGB Dash 2026 — Stepper Wheel Implementation
 *
 * Ported from prototype SpeedometerWheel.cpp.
 * All Serial.println replaced with ESP_LOGx macros.
 * All hardcoded pins replaced with init() parameters.
 */

#include "StepperWheel.h"
#include "esp_log.h"

static const char* TAG = "StepperWheel";

// ════════════════════════════════════════════════════════════════════════
// Initialization
// ════════════════════════════════════════════════════════════════════════

void StepperWheel::init(int in1, int in2, int in3, int in4, int endstopPin) {
    in1_ = in1;
    in2_ = in2;
    in3_ = in3;
    in4_ = in4;
    endstopPin_ = endstopPin;

    // 28BYJ-48 requires pin order IN1, IN3, IN2, IN4 for the Arduino Stepper lib
    stepper_ = new Stepper(STEPS_PER_REVOLUTION, in1, in3, in2, in4);
    stepper_->setSpeed(STEPPER_RPM);

    pinMode(endstopPin_, INPUT_PULLUP);

    currentPosition_ = 0;
    currentPosF_     = 0.0f;

    ESP_LOGI(TAG, "Init: pins IN1=%d IN2=%d IN3=%d IN4=%d, home=%d",
             in1, in2, in3, in4, endstopPin);
    ESP_LOGI(TAG, "Stepper: %d steps/rev, %d RPM, %d steps/MPH",
             STEPS_PER_REVOLUTION, STEPPER_RPM, STEPS_PER_MPH);
}

// ════════════════════════════════════════════════════════════════════════
// Endstop reading
// ════════════════════════════════════════════════════════════════════════

bool StepperWheel::readEndstop() {
    return digitalRead(endstopPin_) == HIGH;  // HIGH = marker detected
}

// ════════════════════════════════════════════════════════════════════════
// Single step
// ════════════════════════════════════════════════════════════════════════

void StepperWheel::singleStep(bool clockwise) {
    stepper_->step(clockwise ? 1 : -1);
    currentPosition_ += clockwise ? 1 : -1;

    if (currentPosition_ >= STEPS_PER_REVOLUTION) {
        currentPosition_ = 0;
    } else if (currentPosition_ < 0) {
        currentPosition_ = STEPS_PER_REVOLUTION - 1;
    }
}

// ════════════════════════════════════════════════════════════════════════
// Edge finding (for home calibration)
// ════════════════════════════════════════════════════════════════════════

int StepperWheel::findEdge(bool clockwise, bool risingEdge) {
    bool targetState = risingEdge;
    bool currentState = readEndstop();

    ESP_LOGD(TAG, "Finding %s edge, start state=%s",
             risingEdge ? "rising" : "falling",
             currentState ? "TRIGGERED" : "OPEN");

    // Search up to 1.5 revolutions
    for (int i = 0; i < (STEPS_PER_REVOLUTION * 3 / 2); i++) {
        singleStep(clockwise);
        delay(5);

        bool newState = readEndstop();

        if (i % 100 == 0) {
            ESP_LOGD(TAG, "Step %d/%d sensor=%s",
                     i, STEPS_PER_REVOLUTION * 3 / 2,
                     newState ? "TRIGGERED" : "OPEN");
        }

        if (currentState != newState && newState == targetState) {
            ESP_LOGI(TAG, "Edge found at step %d", currentPosition_);
            return currentPosition_;
        }
        currentState = newState;
    }

    ESP_LOGW(TAG, "Edge not found after 1.5 revolutions");
    return -1;
}

// ════════════════════════════════════════════════════════════════════════
// Home calibration
// ════════════════════════════════════════════════════════════════════════

bool StepperWheel::calibrateHome() {
    ESP_LOGI(TAG, "Starting home calibration...");

    bool initialState = readEndstop();
    ESP_LOGI(TAG, "Initial sensor state: %s",
             initialState ? "TRIGGERED" : "OPEN");

    // Phase 1: find rising edge (entering marker)
    ESP_LOGI(TAG, "Phase 1: finding rising edge (CW)...");
    homeStartPos_ = findEdge(true, true);

    if (homeStartPos_ == -1) {
        ESP_LOGW(TAG, "Not found CW, trying CCW...");
        homeStartPos_ = findEdge(false, true);
    }

    if (homeStartPos_ == -1) {
        ESP_LOGE(TAG, "Home marker start not found!");
        return false;
    }

    ESP_LOGI(TAG, "Marker starts at step %d", homeStartPos_);

    // Phase 2: find falling edge (leaving marker)
    ESP_LOGI(TAG, "Phase 2: finding falling edge...");
    homeEndPos_ = findEdge(true, false);
    if (homeEndPos_ == -1) {
        ESP_LOGE(TAG, "Home marker end not found!");
        return false;
    }

    ESP_LOGI(TAG, "Marker ends at step %d", homeEndPos_);

    // Calculate marker width
    homeMarkerWidth_ = (homeEndPos_ - homeStartPos_ + STEPS_PER_REVOLUTION)
                       % STEPS_PER_REVOLUTION;
    ESP_LOGI(TAG, "Marker width: %d steps", homeMarkerWidth_);

    // Move to center of marker
    int centerOffset = homeMarkerWidth_ / 2;
    int centerPos = (homeStartPos_ + centerOffset) % STEPS_PER_REVOLUTION;

    int stepsToMove = (centerPos - currentPosition_ + STEPS_PER_REVOLUTION)
                      % STEPS_PER_REVOLUTION;
    if (stepsToMove > STEPS_PER_REVOLUTION / 2) {
        stepsToMove -= STEPS_PER_REVOLUTION;
    }

    stepper_->step(stepsToMove);
    currentPosition_ = centerPos;
    currentPosF_     = (float)centerPos;

    calibrated_ = true;
    ESP_LOGI(TAG, "Home calibration complete (center=%d)", centerPos);
    return true;
}

// ════════════════════════════════════════════════════════════════════════
// Move to MPH (starts eased transition)
// ════════════════════════════════════════════════════════════════════════

void StepperWheel::moveToMPH(int mph) {
    if (!calibrated_) {
        ESP_LOGW(TAG, "Not calibrated — ignoring moveToMPH(%d)", mph);
        return;
    }

    mph = constrain(mph, MIN_SPEED_MPH, MAX_SPEED_MPH);

    int targetSteps = stepsFromHome(mph);
    int homeCenter = (homeStartPos_ + homeMarkerWidth_ / 2) % STEPS_PER_REVOLUTION;
    targetPosition_ = (homeCenter + targetSteps) % STEPS_PER_REVOLUTION;

    // Already at target — skip
    if (abs(targetPosition_ - (int)round(currentPosF_)) < 2) {
        return;
    }

    // Start smooth transition
    startPosF_  = currentPosF_;
    targetPosF_ = (float)targetPosition_;

    // Shortest path wrap-around
    if (fabsf(targetPosF_ - startPosF_) > STEPS_PER_REVOLUTION / 2) {
        if (targetPosF_ > startPosF_) {
            targetPosF_ -= STEPS_PER_REVOLUTION;
        } else {
            targetPosF_ += STEPS_PER_REVOLUTION;
        }
    }

    transitionStart_ = millis();
    moving_ = true;

    ESP_LOGD(TAG, "Transition to %d MPH (target step %d)", mph, targetPosition_);
}

// ════════════════════════════════════════════════════════════════════════
// Update (call every loop iteration)
// ════════════════════════════════════════════════════════════════════════

void StepperWheel::update() {
    if (!calibrated_ || !moving_) return;

    unsigned long elapsed = millis() - transitionStart_;

    if (elapsed >= TRANSITION_TIME_MS) {
        // Transition complete
        currentPosF_ = targetPosF_;

        while (currentPosF_ >= STEPS_PER_REVOLUTION) currentPosF_ -= STEPS_PER_REVOLUTION;
        while (currentPosF_ < 0)                     currentPosF_ += STEPS_PER_REVOLUTION;

        currentPosition_ = (int)round(currentPosF_);
        moving_ = false;

        ESP_LOGD(TAG, "Transition complete, pos=%d (%d MPH)",
                 currentPosition_, getCurrentMPH());
    } else {
        float progress = (float)elapsed / (float)TRANSITION_TIME_MS;
        float eased    = easeInOutCubic(progress);
        currentPosF_   = startPosF_ + (targetPosF_ - startPosF_) * eased;
    }

    updateStepperPosition();
}

// ════════════════════════════════════════════════════════════════════════
// Easing
// ════════════════════════════════════════════════════════════════════════

float StepperWheel::easeInOutCubic(float t) {
    if (t < 0.5f) {
        return 4.0f * t * t * t;
    } else {
        float f = (2.0f * t - 2.0f);
        return 1.0f + f * f * f / 2.0f;
    }
}

// ════════════════════════════════════════════════════════════════════════
// Internal position update (drives actual stepper steps)
// ════════════════════════════════════════════════════════════════════════

void StepperWheel::updateStepperPosition() {
    int targetSteps = (int)round(currentPosF_);

    while (targetSteps >= STEPS_PER_REVOLUTION) targetSteps -= STEPS_PER_REVOLUTION;
    while (targetSteps < 0)                     targetSteps += STEPS_PER_REVOLUTION;

    int stepsToMove = shortestPath(currentPosition_, targetSteps);

    if (stepsToMove != 0) {
        stepper_->step(stepsToMove);
        currentPosition_ = targetSteps;
    }
}

int StepperWheel::shortestPath(int from, int to) {
    int diff = (to - from + STEPS_PER_REVOLUTION) % STEPS_PER_REVOLUTION;
    if (diff > STEPS_PER_REVOLUTION / 2) {
        diff -= STEPS_PER_REVOLUTION;
    }
    return diff;
}

int StepperWheel::stepsFromHome(int mph) {
    return ZERO_MPH_OFFSET + (mph * STEPS_PER_MPH);
}

// ════════════════════════════════════════════════════════════════════════
// Current MPH from step position
// ════════════════════════════════════════════════════════════════════════

int StepperWheel::getCurrentMPH() const {
    if (!calibrated_) return 0;

    int homeCenter = (homeStartPos_ + homeMarkerWidth_ / 2) % STEPS_PER_REVOLUTION;
    int currentPos = (int)round(currentPosF_);
    while (currentPos >= STEPS_PER_REVOLUTION) currentPos -= STEPS_PER_REVOLUTION;
    while (currentPos < 0)                     currentPos += STEPS_PER_REVOLUTION;

    int stepsFromCenter = (currentPos - homeCenter + STEPS_PER_REVOLUTION)
                          % STEPS_PER_REVOLUTION;
    if (stepsFromCenter > STEPS_PER_REVOLUTION / 2) {
        stepsFromCenter -= STEPS_PER_REVOLUTION;
    }

    int stepsFromZero = stepsFromCenter - ZERO_MPH_OFFSET;
    return constrain(stepsFromZero / STEPS_PER_MPH, MIN_SPEED_MPH, MAX_SPEED_MPH);
}

// ════════════════════════════════════════════════════════════════════════
// Test helpers
// ════════════════════════════════════════════════════════════════════════

void StepperWheel::testStepperMotor() {
    ESP_LOGI(TAG, "=== STEPPER MOTOR TEST ===");
    ESP_LOGI(TAG, "10 steps clockwise...");

    for (int i = 0; i < 10; i++) {
        bool state = readEndstop();
        ESP_LOGD(TAG, "Step %d/10 sensor=%s",
                 i + 1, state ? "TRIGGERED" : "OPEN");
        stepper_->step(1);
        delay(100);
    }

    ESP_LOGI(TAG, "Stepper test complete");
}

void StepperWheel::manualStepperTest() {
    ESP_LOGI(TAG, "=== MANUAL STEPPER TEST (bypass library) ===");

    pinMode(in1_, OUTPUT);
    pinMode(in2_, OUTPUT);
    pinMode(in3_, OUTPUT);
    pinMode(in4_, OUTPUT);

    // 28BYJ-48 full-step sequence
    static const int seq[4][4] = {
        {1, 0, 0, 1},
        {1, 1, 0, 0},
        {0, 1, 1, 0},
        {0, 0, 1, 1},
    };

    for (int s = 0; s < 20; s++) {
        int idx = s % 4;
        digitalWrite(in1_, seq[idx][0]);
        digitalWrite(in2_, seq[idx][1]);
        digitalWrite(in3_, seq[idx][2]);
        digitalWrite(in4_, seq[idx][3]);
        delay(100);
    }

    // All coils off
    digitalWrite(in1_, 0);
    digitalWrite(in2_, 0);
    digitalWrite(in3_, 0);
    digitalWrite(in4_, 0);

    ESP_LOGI(TAG, "Manual stepper test complete");
}
