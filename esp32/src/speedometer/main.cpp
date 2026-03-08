/**
 * MGB Dash 2026 — Speedometer Main
 *
 * CAN-driven mechanical speedometer:
 *   - 28BYJ-48 stepper needle (StepperWheel lib, cubic-eased)
 *   - Servo gear indicator disc (ServoGauge lib)
 *   - SK6812 RGBW LED ring (turn signals, hazards, ambient)
 *   - SSD1306 OLED odometer (128x64, I2C, integrated on ESP32 board)
 *
 * All speed/gear/odometer data comes from body controller via CAN —
 * no local sensor logic.
 */

#include <Arduino.h>
#include <Wire.h>
#include <cmath>
#include "esp_log.h"
#include "Adafruit_SSD1306.h"
#include "CanBus.h"
#include "Heartbeat.h"
#include "CanLog.h"
#include "LedRing.h"
#include "ServoGauge.h"
#include "StepperWheel.h"
#include "can_ids.h"

static const char* TAG = GAUGE_ROLE_NAME;

CanBus      canBus;
Heartbeat   heartbeat;
CanLog      canLog;
LedRing     ledRing;
ServoGauge  gearServo;
StepperWheel stepperWheel;

// ── OLED odometer (SSD1306 128x64, I2C) ──────────────────────────────
static constexpr int OLED_WIDTH  = 128;
static constexpr int OLED_HEIGHT = 64;
Adafruit_SSD1306 oled(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);  // no dedicated RST pin on ideaspark board
bool     oledReady     = false;
double   odometerMiles = 0.0;

// ── Diagnostic state machine ────────────────────────────────────────
enum DiagState { STATE_INIT, STATE_HOME, STATE_TEST, STATE_IDLE, STATE_RUN, STATE_ERR };
static const char* const STATE_NAMES[] = { "INIT", "HOME", "TEST", "IDLE", "RUN", "ERR" };
DiagState diagState = STATE_INIT;

// ── Tracked CAN values for diagnostics ──────────────────────────────
int      currentMPH  = 0;
uint8_t  currentGear = GEAR_NEUTRAL;
uint32_t canRxCount  = 0;

// ── OLED refresh timer ──────────────────────────────────────────────
unsigned long lastOledRefreshMs = 0;
static constexpr unsigned long OLED_REFRESH_MS = 250;

// ── Onboard LED heartbeat (GPIO2, 1 Hz) ─────────────────────────────
static constexpr int PIN_ONBOARD_LED = 2;
unsigned long lastLedToggleMs = 0;
bool onboardLedState = false;

// ── CAN silence watchdog ────────────────────────────────────────────
bool canMessageReceived = false;
bool canSilenceMode     = false;
unsigned long lastFaultProbeMs = 0;
static constexpr unsigned long FAULT_PROBE_INTERVAL_MS = 3000;

// ── Turn signal / hazard holdoff ────────────────────────────────────
unsigned long lastLeftMs   = 0;
unsigned long lastRightMs  = 0;
unsigned long lastHazardMs = 0;
static constexpr unsigned long TURN_HOLDOFF_MS = 600;

enum AnimState { ANIM_NONE, ANIM_HAZARD, ANIM_LEFT, ANIM_RIGHT };
AnimState currentAnim = ANIM_NONE;

// ── Body state flags (from 0x710) ───────────────────────────────────
uint8_t lastBodyFlags = 0;

// ── Gear angle lookup ───────────────────────────────────────────────
// Servo angles for gear indicator disc
static constexpr int GEAR_ANGLES[] = {
    15,   // GEAR_NEUTRAL (0)
    30,   // GEAR_1 (1)
    45,   // GEAR_2 (2)
    60,   // GEAR_3 (3)
    75,   // GEAR_4 (4)
};
static constexpr int GEAR_ANGLE_REVERSE = 0;
static constexpr int GEAR_ANGLE_UNKNOWN = 15;  // show neutral

// ── Color wheel helper ──────────────────────────────────────────────
static void wheelToRGB(uint8_t pos, uint8_t &r, uint8_t &g, uint8_t &b) {
    if (pos < 85) {
        r = 255 - pos * 3;
        g = pos * 3;
        b = 0;
    } else if (pos < 170) {
        pos -= 85;
        r = 0;
        g = 255 - pos * 3;
        b = pos * 3;
    } else {
        pos -= 170;
        r = pos * 3;
        g = 0;
        b = 255 - pos * 3;
    }
}

// ═════════════════════════════════════════════════════════════════════
// OLED splash screen (role + version, shown at boot for 2 seconds)
// ═════════════════════════════════════════════════════════════════════
static void oledDrawSplash() {
    if (!oledReady) return;
    oled.clearDisplay();
    oled.setTextColor(SSD1306_WHITE);

    // Role name in yellow zone (y=0, size 2 = 16px, fits perfectly)
    oled.setTextSize(2);
    int16_t x1, y1;
    uint16_t w, h;
    oled.getTextBounds(GAUGE_ROLE_NAME, 0, 0, &x1, &y1, &w, &h);
    oled.setCursor((OLED_WIDTH - w) / 2, 0);
    oled.print(GAUGE_ROLE_NAME);

    // Version in blue zone (centered)
    char verBuf[24];
    snprintf(verBuf, sizeof(verBuf), "v%d.%s.%.7s",
             VERSION_MILESTONE, VERSION_DATE, VERSION_HASH);
    oled.setTextSize(1);
    oled.getTextBounds(verBuf, 0, 0, &x1, &y1, &w, &h);
    oled.setCursor((OLED_WIDTH - w) / 2, 30);
    oled.print(verBuf);

    oled.display();
}

// ═════════════════════════════════════════════════════════════════════
// OLED diagnostic display (two-zone layout)
//   Yellow band (y=0-15):  state word + CAN rx count
//   Blue zone  (y=16-63):  MPH, gear, odometer, version
// ═════════════════════════════════════════════════════════════════════
static void oledDrawDiagnostics() {
    if (!oledReady) return;
    oled.clearDisplay();
    oled.setTextColor(SSD1306_WHITE);

    // ── Yellow zone (0-15): state name (size 2) + rx count (size 1) ──
    oled.setTextSize(2);
    oled.setCursor(0, 0);
    oled.print(STATE_NAMES[diagState]);

    // CAN rx count — right-aligned, size 1, vertically centered in yellow
    char rxBuf[12];
    snprintf(rxBuf, sizeof(rxBuf), "%lu", (unsigned long)canRxCount);
    oled.setTextSize(1);
    int rxLen = strlen(rxBuf) * 6;
    oled.setCursor(OLED_WIDTH - rxLen, 4);
    oled.print(rxBuf);

    // ── Blue zone (16-63): diagnostic values ─────────────────────────
    char buf[22];

    // Line 1 (y=18): MPH + Gear
    const char* gearStr;
    if (lastBodyFlags & BODY_FLAG_REVERSE) {
        gearStr = "R";
    } else {
        switch (currentGear) {
            case GEAR_1: gearStr = "1"; break;
            case GEAR_2: gearStr = "2"; break;
            case GEAR_3: gearStr = "3"; break;
            case GEAR_4: gearStr = "4"; break;
            default:     gearStr = "N"; break;
        }
    }
    snprintf(buf, sizeof(buf), "MPH %-3d    GEAR %s", currentMPH, gearStr);
    oled.setCursor(0, 18);
    oled.print(buf);

    // Line 2 (y=28): Odometer
    snprintf(buf, sizeof(buf), "ODO %.1f mi", odometerMiles);
    oled.setCursor(0, 28);
    oled.print(buf);

    // Line 3 (y=40): Stepper status
    snprintf(buf, sizeof(buf), "NEEDLE %d MPH %s",
             stepperWheel.getCurrentMPH(),
             stepperWheel.isCalibrated() ? "CAL" : "UNCAL");
    oled.setCursor(0, 40);
    oled.print(buf);

    // Line 4 (y=54): Version
    snprintf(buf, sizeof(buf), "v%d.%s.%.7s",
             VERSION_MILESTONE, VERSION_DATE, VERSION_HASH);
    oled.setCursor(0, 54);
    oled.print(buf);

    oled.display();
}

// ═════════════════════════════════════════════════════════════════════
// Self-test: stepper sweep + LED chase + servo sweep + OLED test
// ═════════════════════════════════════════════════════════════════════
void runSelfTest() {
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_START);
    ESP_LOGI(TAG, "Self-test starting...");

    const int degreesPerLed = 180 / LED_COUNT;

    // ── Phase 1: Servo sweep up + LED rainbow fill ──────────────────
    for (int a = 0; a <= 180; a += 2) {
        gearServo.writeDirect(a);

        int litCount = a / degreesPerLed;
        for (int i = 0; i < LED_COUNT; i++) {
            if (i <= litCount) {
                uint8_t r, g, b;
                wheelToRGB((i * 256) / LED_COUNT, r, g, b);
                ledRing.setPixel(i, r, g, b);
            } else {
                ledRing.setPixel(i, 0, 0, 0);
            }
        }
        ledRing.show();
        delay(8);
    }

    // ── Phase 2: Hold + white flash ─────────────────────────────────
    ledRing.setAll(255, 255, 255);
    ledRing.show();
    delay(150);
    for (int i = 0; i < LED_COUNT; i++) {
        uint8_t r, g, b;
        wheelToRGB((i * 256) / LED_COUNT, r, g, b);
        ledRing.setPixel(i, r, g, b);
    }
    ledRing.show();
    delay(150);

    // ── Phase 3: Servo sweep down + LEDs extinguish ─────────────────
    for (int a = 180; a >= 0; a -= 2) {
        gearServo.writeDirect(a);

        int litCount = a / degreesPerLed;
        for (int i = 0; i < LED_COUNT; i++) {
            if (i <= litCount) {
                uint8_t r, g, b;
                wheelToRGB((i * 256) / LED_COUNT, r, g, b);
                ledRing.setPixel(i, r, g, b);
            } else {
                ledRing.setPixel(i, 0, 0, 0);
            }
        }
        ledRing.show();
        delay(8);
    }

    // ── Phase 4: Stepper sweep 0→45→0 MPH ──────────────────────────
    if (stepperWheel.isCalibrated()) {
        stepperWheel.moveToMPH(45);
        while (stepperWheel.isInTransition()) {
            stepperWheel.update();
            delay(10);
        }
        stepperWheel.moveToMPH(0);
        while (stepperWheel.isInTransition()) {
            stepperWheel.update();
            delay(10);
        }
    }

    // ── Phase 5: Double green flash (pass indicator) ────────────────
    ledRing.setAll(0, 0, 0);
    ledRing.show();
    delay(100);
    for (int f = 0; f < 2; f++) {
        ledRing.setAll(0, 255, 0);
        ledRing.show();
        delay(150);
        ledRing.setAll(0, 0, 0);
        ledRing.show();
        delay(150);
    }

    // ── Phase 6: OLED test pattern ──────────────────────────────────
    if (oledReady) {
        oled.clearDisplay();
        oled.fillRect(0, 0, OLED_WIDTH, OLED_HEIGHT, SSD1306_WHITE);
        oled.display();
        delay(200);
        oled.clearDisplay();
        oled.setTextColor(SSD1306_WHITE);
        oled.setTextSize(2);
        int16_t x1, y1;
        uint16_t w, h;
        oled.getTextBounds("DIAG OK", 0, 0, &x1, &y1, &w, &h);
        oled.setCursor((OLED_WIDTH - w) / 2, (OLED_HEIGHT - h) / 2);
        oled.print("DIAG OK");
        oled.display();
        delay(500);
    }

    gearServo.writeDirect(0);
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_PASS);
    ESP_LOGI(TAG, "Self-test complete.");
}

// ═════════════════════════════════════════════════════════════════════
// Turn signal / hazard animation (same pattern as servo_gauge)
// ═════════════════════════════════════════════════════════════════════
static void updateAnimations() {
    unsigned long now = millis();

    if (lastBodyFlags & BODY_FLAG_HAZARD)     lastHazardMs = now;
    if (lastBodyFlags & BODY_FLAG_LEFT_TURN)  lastLeftMs   = now;
    if (lastBodyFlags & BODY_FLAG_RIGHT_TURN) lastRightMs  = now;

    bool hazardActive = lastHazardMs > 0 && (now - lastHazardMs) < TURN_HOLDOFF_MS;
    bool leftActive   = lastLeftMs   > 0 && (now - lastLeftMs)   < TURN_HOLDOFF_MS;
    bool rightActive  = lastRightMs  > 0 && (now - lastRightMs)  < TURN_HOLDOFF_MS;

    AnimState desired = ANIM_NONE;
    if (hazardActive)      desired = ANIM_HAZARD;
    else if (leftActive)   desired = ANIM_LEFT;
    else if (rightActive)  desired = ANIM_RIGHT;

    if (desired != currentAnim) {
        switch (desired) {
            case ANIM_HAZARD: ledRing.startHazard();          break;
            case ANIM_LEFT:   ledRing.startTurnSignal(true);  break;
            case ANIM_RIGHT:  ledRing.startTurnSignal(false); break;
            case ANIM_NONE:   ledRing.stopAnimation();        break;
        }
        currentAnim = desired;
    }
}

// ═════════════════════════════════════════════════════════════════════
// Setup
// ═════════════════════════════════════════════════════════════════════

void setup() {
    Serial.begin(115200);

    // ── Onboard LED (activity heartbeat) ─────────────────────────────
    pinMode(PIN_ONBOARD_LED, OUTPUT);
    digitalWrite(PIN_ONBOARD_LED, LOW);

    char versionStr[48];
    snprintf(versionStr, sizeof(versionStr), "%s v%d.%s.%s",
             GAUGE_ROLE_NAME, VERSION_MILESTONE, VERSION_DATE, VERSION_HASH);
    ESP_LOGI(TAG, "%s starting...", versionStr);

    canLog.init(&canBus, LOG_ROLE);
    canLog.log(LogLevel::LOG_CRITICAL, LogEvent::BOOT_START, 0, versionStr);

    canBus.init(PIN_CAN_TX, PIN_CAN_RX, CAN_BUS_SPEED);
    heartbeat.init(&canBus, GAUGE_ROLE_NAME);
    ledRing.init(PIN_LED_DATA, LED_COUNT);

    // ── OLED init + splash screen ────────────────────────────────────
    Wire.begin(PIN_OLED_SDA, PIN_OLED_SCL);
    if (oled.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
        oledReady = true;
        ESP_LOGI(TAG, "OLED init OK (128x64 @ 0x3C)");
        oledDrawSplash();
        delay(2000);
    } else {
        ESP_LOGW(TAG, "OLED init FAILED — diagnostic display unavailable");
    }

    // ── Stepper needle ──────────────────────────────────────────────
    diagState = STATE_HOME;
    stepperWheel.init(PIN_STEPPER_IN1, PIN_STEPPER_IN2,
                      PIN_STEPPER_IN3, PIN_STEPPER_IN4,
                      PIN_STEPPER_HOME);

    bool homed = stepperWheel.calibrateHome();
    if (homed) {
        canLog.log(LogLevel::LOG_INFO, LogEvent::STEPPER_HOME_OK);
        ESP_LOGI(TAG, "Stepper homed successfully");
    } else {
        canLog.log(LogLevel::LOG_WARN, LogEvent::STEPPER_HOME_FAIL);
        ESP_LOGW(TAG, "Stepper homing FAILED — needle may be misaligned");
    }

    // ── Gear indicator servo ────────────────────────────────────────
    gearServo.init(PIN_SERVO);
    gearServo.setRange(0.0f, 90.0f);     // angle range for gear disc
    gearServo.setSmoothing(0.3f);         // snappy — gear changes are discrete

    // ── Self-test ───────────────────────────────────────────────────
    diagState = STATE_TEST;
    runSelfTest();

    // ── Park gear servo at neutral ──────────────────────────────────
    gearServo.setAngle(GEAR_ANGLES[GEAR_NEUTRAL]);

    diagState = STATE_IDLE;
    canLog.log(LogLevel::LOG_INFO, LogEvent::BOOT_COMPLETE, millis());
    ESP_LOGI(TAG, "Init complete.");
}

// ═════════════════════════════════════════════════════════════════════
// Loop
// ═════════════════════════════════════════════════════════════════════

void loop() {
    canBus.checkErrors();
    heartbeat.update();

    // ── CAN receive — drain queue ───────────────────────────────────
    uint32_t id;
    uint8_t  data[8];
    uint8_t  len;
    while (canBus.receive(id, data, len)) {
        canMessageReceived = true;
        canRxCount++;

        switch (id) {

        // ── Speed → stepper needle ──────────────────────────────────
        case CAN_ID_BODY_SPEED: {
            double mph;
            memcpy(&mph, data, sizeof(double));
            currentMPH = (int)mph;
            stepperWheel.moveToMPH(currentMPH);
            break;
        }

        // ── Gear → servo indicator disc ─────────────────────────────
        case CAN_ID_BODY_GEAR: {
            uint8_t gear = data[0];
            currentGear = gear;
            int angle;
            if (gear == GEAR_UNKNOWN) {
                angle = GEAR_ANGLE_UNKNOWN;
            } else if (gear <= GEAR_4) {
                angle = GEAR_ANGLES[gear];
            } else {
                angle = GEAR_ANGLE_UNKNOWN;
            }
            // Check reverse flag from body state
            if (lastBodyFlags & BODY_FLAG_REVERSE) {
                angle = GEAR_ANGLE_REVERSE;
            }
            gearServo.setAngle(angle);
            break;
        }

        // ── Odometer ─────────────────────────────────────────────────
        case CAN_ID_BODY_ODOMETER: {
            double miles;
            memcpy(&miles, data, sizeof(double));
            odometerMiles = miles;
            break;
        }

        // ── GPS speed → future discrepancy check ────────────────────
        case CAN_ID_GPS_SPEED:
            // TODO: compare with body speed for sensor validation
            break;

        // ── Ambient light → LED brightness ──────────────────────────
        case CAN_ID_GPS_AMBIENT_LIGHT:
            ledRing.setAmbientFromCategory(data[0]);
            break;

        // ── Body state → turn signal / hazard animations ────────────
        case CAN_ID_BODY_STATE:
            lastBodyFlags = data[0];
            break;

        // ── On-demand self-test ─────────────────────────────────────
        case CAN_ID_SELF_TEST: {
            uint8_t target = data[0];
            if (target == SELF_TEST_TARGET_ALL ||
                target == static_cast<uint8_t>(LOG_ROLE)) {
                runSelfTest();
            }
            break;
        }

        default:
            break;
        }
    }

    // ── Update all actuators ────────────────────────────────────────
    stepperWheel.update();
    gearServo.update();
    updateAnimations();
    ledRing.update();

    // ── State tracking ───────────────────────────────────────────────
    if (canMessageReceived && diagState == STATE_IDLE) {
        diagState = STATE_RUN;
    }

    // ── OLED diagnostic refresh (periodic) ───────────────────────────
    unsigned long now = millis();
    if (now - lastOledRefreshMs >= OLED_REFRESH_MS) {
        lastOledRefreshMs = now;
        oledDrawDiagnostics();
    }

    // ── Onboard LED heartbeat (1 Hz toggle) ──────────────────────────
    if (now - lastLedToggleMs >= 500) {
        lastLedToggleMs = now;
        onboardLedState = !onboardLedState;
        digitalWrite(PIN_ONBOARD_LED, onboardLedState ? HIGH : LOW);
    }

    // ── CAN silence watchdog ────────────────────────────────────────
    if (!canMessageReceived && millis() > CAN_SILENCE_TIMEOUT_MS) {
        if (!canSilenceMode) {
            canSilenceMode = true;
            lastFaultProbeMs = now;
            diagState = STATE_ERR;
            ledRing.startBluePulse();
            canLog.log(LogLevel::LOG_WARN, LogEvent::CAN_SILENCE);
            ESP_LOGW(TAG, "CAN silence — entering fault mode");
        } else if ((now - lastFaultProbeMs) > FAULT_PROBE_INTERVAL_MS) {
            lastFaultProbeMs = now;

            twai_status_info_t status;
            if (canBus.getStatus(status)) {
                static const char* stateNames[] = {
                    "STOPPED", "RUNNING", "BUS_OFF", "RECOVERING"
                };
                const char* stateName = (status.state <= TWAI_STATE_RECOVERING)
                    ? stateNames[status.state] : "UNKNOWN";
                ESP_LOGW(TAG, "Fault probe: state=%s tx_err_hw=%lu rx_err_hw=%lu "
                         "tx_failed=%lu rx_missed=%lu arb_lost=%lu bus_err=%lu "
                         "msgs_to_tx=%lu msgs_to_rx=%lu",
                         stateName,
                         status.tx_error_counter, status.rx_error_counter,
                         status.tx_failed_count, status.rx_missed_count,
                         status.arb_lost_count, status.bus_error_count,
                         status.msgs_to_tx, status.msgs_to_rx);
            } else {
                ESP_LOGW(TAG, "Fault probe: bus_off=%d tx_err=%lu rx_err=%lu (status read failed)",
                         canBus.isBusOff(), canBus.getTxErrorCount(), canBus.getRxErrorCount());
            }
            canBus.checkErrors();
        }
    }
    if (canMessageReceived && canSilenceMode) {
        canSilenceMode = false;
        diagState = STATE_RUN;
        ledRing.stopBluePulse();
        canLog.log(LogLevel::LOG_INFO, LogEvent::BUS_RECOVERED);
        ESP_LOGI(TAG, "CAN traffic resumed");
    }
}
