/**
 * MGB Dash 2026 — Servo Gauge Main
 *
 * Shared entry point for FUEL, AMPS, and TEMP servo gauges.
 * Build-time constant GAUGE_ROLE selects behavior.
 * Optional OLED diagnostic display when HAS_OLED is defined
 * (ideaspark ESP32+OLED board, SSD1306 128x64 I2C).
 */

#include <Arduino.h>
#include <cmath>
#include "esp_log.h"
#include "CanBus.h"
#include "Heartbeat.h"
#include "CanLog.h"
#include "LedRing.h"
#include "ServoGauge.h"
#include "LeafCan.h"
#include "can_ids.h"
#ifdef HAS_OLED
#include <Wire.h>
#include "Adafruit_SSD1306.h"
#endif

static const char* TAG = GAUGE_ROLE_NAME;
static constexpr LogRole ROLE = LOG_ROLE;

CanBus canBus;
Heartbeat heartbeat;
CanLog canLog;
LedRing ledRing;
ServoGauge servo;
LeafCan leafCan;

// ── CAN silence watchdog ────────────────────────────────────────────
unsigned long lastCanRxMs = 0;
bool canSilenceMode = false;
unsigned long lastFaultProbeMs = 0;
static constexpr unsigned long FAULT_PROBE_INTERVAL_MS = 3000;  // log + retry every 3s

// ── Gauge value state ──────────────────────────────────────────────
float gaugeValue = 0.0f;
float lastLoggedGaugeValue = 0.0f;
unsigned long lastGaugeUpdateMs = 0;
static constexpr unsigned long GAUGE_STALE_MS = 2000;
static constexpr float GAUGE_LOG_DEADBAND = 2.0f;  // log when value changes by ≥2A

// ── Turn signal / hazard holdoff ───────────────────────────────────
unsigned long lastLeftMs = 0;
unsigned long lastRightMs = 0;
unsigned long lastHazardMs = 0;
static constexpr unsigned long TURN_HOLDOFF_MS = 600;

// ── Turn blink pixel ranges (pixel 0 = 12 o'clock, clockwise) ────
// TODO: refactor blink animation into a standalone function that
//       accepts elapsed-ms, so Fuel and Amps share one implementation.
static constexpr int RIGHT_BLINK_START = 1;   // pixels 1–5 = right half
static constexpr int RIGHT_BLINK_END   = 5;
static constexpr int LEFT_BLINK_START  = 7;   // pixels 7–11 = left half
static constexpr int LEFT_BLINK_END    = 11;

enum AnimState { ANIM_NONE, ANIM_HAZARD, ANIM_LEFT, ANIM_RIGHT };
AnimState currentAnim = ANIM_NONE;

// ── Body state flags (from 0x710) ──────────────────────────────────
uint8_t lastBodyFlags = 0;

// ── CAN RX counter (for diagnostics) ──────────────────────────────
uint32_t canRxCount = 0;

#ifdef HAS_OLED
// ── OLED diagnostic display (SSD1306 128x64, I2C) ─────────────────
static constexpr int OLED_WIDTH  = 128;
static constexpr int OLED_HEIGHT = 64;
Adafruit_SSD1306 oled(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
bool oledReady = false;

unsigned long lastOledRefreshMs = 0;
static constexpr unsigned long OLED_REFRESH_MS = 250;

// Onboard LED heartbeat (GPIO2, 1 Hz)
static constexpr int PIN_ONBOARD_LED = 2;
unsigned long lastLedToggleMs = 0;
bool onboardLedState = false;

enum DiagState { STATE_INIT, STATE_TEST, STATE_IDLE, STATE_RUN, STATE_ERR };
static const char* const STATE_NAMES[] = { "INIT", "TEST", "IDLE", "RUN", "ERR" };
DiagState diagState = STATE_INIT;

// ── OLED splash screen ─────────────────────────────────────────────
static void oledDrawSplash() {
    if (!oledReady) return;
    oled.clearDisplay();
    oled.setTextColor(SSD1306_WHITE);

    // Role name in yellow zone (y=0, size 2 = 16px)
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

// ── OLED diagnostic display (two-zone layout) ──────────────────────
//   Yellow band (y=0-15):  state word + CAN rx count
//   Blue zone  (y=16-63):  gauge value, CAN stats, version
static void oledDrawDiagnostics() {
    if (!oledReady) return;
    oled.clearDisplay();
    oled.setTextColor(SSD1306_WHITE);

    // ── Yellow zone (0-15): state name (size 2) + rx count (size 1) ──
    oled.setTextSize(2);
    oled.setCursor(0, 0);
    oled.print(STATE_NAMES[diagState]);

    // CAN rx count — right-aligned, size 1, last 4 digits only
    char rxBuf[8];
    snprintf(rxBuf, sizeof(rxBuf), "%04lu", (unsigned long)(canRxCount % 10000));
    oled.setTextSize(1);
    int rxLen = strlen(rxBuf) * 6;
    oled.setCursor(OLED_WIDTH - rxLen, 4);
    oled.print(rxBuf);

    // ── Blue zone (16-63): diagnostic values ─────────────────────────
    char buf[22];

    // Line 1 (y=18): Gauge value + unit
    if (ROLE == LogRole::FUEL) {
        snprintf(buf, sizeof(buf), "SOC  %.1f %%", gaugeValue);
    } else if (ROLE == LogRole::AMPS) {
        snprintf(buf, sizeof(buf), "AMPS %.1f A", gaugeValue);
    } else if (ROLE == LogRole::TEMP) {
        snprintf(buf, sizeof(buf), "TEMP %.1f C", gaugeValue);
    }
    oled.setCursor(0, 18);
    oled.print(buf);

    // Line 2 (y=28): Servo angle
    snprintf(buf, sizeof(buf), "SERVO %d deg", servo.getCurrentAngle());
    oled.setCursor(0, 28);
    oled.print(buf);

    // Line 3 (y=40): CAN status
    if (canSilenceMode) {
        oled.setCursor(0, 40);
        oled.print("CAN: SILENT");
    } else if (lastGaugeUpdateMs > 0 && (millis() - lastGaugeUpdateMs) > GAUGE_STALE_MS) {
        oled.setCursor(0, 40);
        oled.print("CAN: STALE");
    } else {
        snprintf(buf, sizeof(buf), "CAN: OK  %lums ago",
                 lastCanRxMs > 0 ? (millis() - lastCanRxMs) : 0UL);
        oled.setCursor(0, 40);
        oled.print(buf);
    }

    // Line 4 (y=54): Version
    snprintf(buf, sizeof(buf), "v%d.%s.%.7s",
             VERSION_MILESTONE, VERSION_DATE, VERSION_HASH);
    oled.setCursor(0, 54);
    oled.print(buf);

    oled.display();
}
#endif

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

// ── Coordinated self-test ───────────────────────────────────────────
// Sweep needle 0→180→0 with synchronized rainbow LED ring animation.
// Total duration ~3.5 seconds.
void runSelfTest() {
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_START);
    ESP_LOGI(TAG, "Self-test starting...");

    const int degreesPerLed = 180 / LED_COUNT;  // 15° per LED for 12 LEDs

    // ── Phase 1: Sweep up (0→180) with rainbow fill ─────────────────
    // LEDs light up progressively as needle passes each position
    for (int a = 0; a <= 180; a += 2) {
        servo.writeDirect(a);

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

    // ── Phase 2: Hold at 180° — white flash ─────────────────────────
    ledRing.setAll(255, 255, 255);
    ledRing.show();
    delay(150);
    // Restore rainbow
    for (int i = 0; i < LED_COUNT; i++) {
        uint8_t r, g, b;
        wheelToRGB((i * 256) / LED_COUNT, r, g, b);
        ledRing.setPixel(i, r, g, b);
    }
    ledRing.show();
    delay(150);

    // ── Phase 3: Sweep down (180→0) — LEDs extinguish in reverse ────
    for (int a = 180; a >= 0; a -= 2) {
        servo.writeDirect(a);

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

    // ── Phase 4: Pass indicator — double green flash ────────────────
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

    servo.writeDirect(0);
    canLog.log(LogLevel::LOG_INFO, LogEvent::SELF_TEST_PASS);
    ESP_LOGI(TAG, "Self-test complete.");
}

// ═════════════════════════════════════════════════════════════════════
// LED warning colors based on gauge value thresholds
// ═════════════════════════════════════════════════════════════════════
static void updateWarnings() {
    // Don't override turn signal / hazard animations
    if (currentAnim != ANIM_NONE) return;

    // Don't override blue pulse fault mode
    if (canSilenceMode) return;

    // Stale data warning (amber) — only after first value received
    if (lastGaugeUpdateMs > 0 && (millis() - lastGaugeUpdateMs) > GAUGE_STALE_MS) {
        ledRing.setWarning(255, 100, 0);
        return;
    }

    if (ROLE == LogRole::FUEL) {
        if (gaugeValue < 10.0f) {
            ledRing.setWarning(255, 0, 0);       // red — critically low SOC
        } else if (gaugeValue < 20.0f) {
            ledRing.setWarning(255, 180, 0);     // amber — low SOC
        } else {
            ledRing.clearWarning();
        }
    } else if (ROLE == LogRole::AMPS) {
        float absAmps = fabsf(gaugeValue);
        if (absAmps > 150.0f) {
            ledRing.setWarning(255, 0, 0);       // red — extreme current
        } else if (absAmps > 100.0f) {
            ledRing.setWarning(255, 180, 0);     // amber — high current
        } else {
            ledRing.clearWarning();
        }
    } else if (ROLE == LogRole::TEMP) {
        if (gaugeValue > 45.0f || gaugeValue < -5.0f) {
            ledRing.setWarning(255, 0, 0);       // red — extreme temp
        } else if (gaugeValue > 35.0f || gaugeValue < 0.0f) {
            ledRing.setWarning(255, 180, 0);     // amber — concerning temp
        } else {
            ledRing.clearWarning();
        }
    }
}

// ═════════════════════════════════════════════════════════════════════
// Turn signal / hazard animation from body controller flags (0x710)
// Uses holdoff timer to bridge relay blink gaps.
// ═════════════════════════════════════════════════════════════════════
static void updateAnimations() {
    // TEMP does not consume turn/hazard signals
    if (ROLE == LogRole::TEMP) return;

    unsigned long now = millis();

    // Update holdoff timestamps from latest body flags
    if (lastBodyFlags & BODY_FLAG_HAZARD)     lastHazardMs = now;
    if (lastBodyFlags & BODY_FLAG_LEFT_TURN)  lastLeftMs   = now;
    if (lastBodyFlags & BODY_FLAG_RIGHT_TURN) lastRightMs  = now;

    bool hazardActive = lastHazardMs > 0 && (now - lastHazardMs) < TURN_HOLDOFF_MS;
    bool leftActive   = lastLeftMs   > 0 && (now - lastLeftMs)   < TURN_HOLDOFF_MS;
    bool rightActive  = lastRightMs  > 0 && (now - lastRightMs)  < TURN_HOLDOFF_MS;

    AnimState desired = ANIM_NONE;
    if (hazardActive) {
        desired = ANIM_HAZARD;
    } else if (ROLE == LogRole::FUEL) {
        // FUEL sits on the left side — only responds to left turn
        if (leftActive) desired = ANIM_LEFT;
    } else if (ROLE == LogRole::AMPS) {
        // AMPS sits on the right side — only responds to right turn
        if (rightActive) desired = ANIM_RIGHT;
    }

    // Only change animation on state transition
    if (desired != currentAnim) {
        static const char* const ANIM_NAMES[] = { "NONE", "HAZARD", "LEFT", "RIGHT" };
        ESP_LOGI(TAG, "Anim: %s -> %s", ANIM_NAMES[currentAnim], ANIM_NAMES[desired]);
        switch (desired) {
            case ANIM_HAZARD: ledRing.startHazard();            break;
            case ANIM_LEFT:
                ledRing.startPartialBlink(LEFT_BLINK_START, LEFT_BLINK_END);
                break;
            case ANIM_RIGHT:
                ledRing.startPartialBlink(RIGHT_BLINK_START, RIGHT_BLINK_END);
                break;
            case ANIM_NONE:   ledRing.stopAnimation();          break;
        }
        currentAnim = desired;
    }
}

void setup() {
    Serial.begin(115200);

#ifdef HAS_OLED
    pinMode(PIN_ONBOARD_LED, OUTPUT);
    digitalWrite(PIN_ONBOARD_LED, LOW);
#endif

    char versionStr[48];
    snprintf(versionStr, sizeof(versionStr), "%s v%d.%s.%s",
             GAUGE_ROLE_NAME, VERSION_MILESTONE, VERSION_DATE, VERSION_HASH);
    ESP_LOGI(TAG, "%s starting...", versionStr);

    canLog.init(&canBus, LOG_ROLE);
    canLog.log(LogLevel::LOG_CRITICAL, LogEvent::BOOT_START, 0, versionStr);

    canBus.init(PIN_CAN_TX, PIN_CAN_RX, CAN_BUS_SPEED);
    heartbeat.init(&canBus, GAUGE_ROLE_NAME);
    ledRing.init(PIN_LED_DATA, LED_COUNT);
    servo.init(PIN_SERVO);

#ifdef HAS_OLED
    // ── OLED init + splash screen ─────────────────────────────────────
    Wire.begin(PIN_OLED_SDA, PIN_OLED_SCL);
    if (oled.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
        oledReady = true;
        ESP_LOGI(TAG, "OLED init OK (128x64 @ 0x3C)");
        oledDrawSplash();
        delay(2000);
    } else {
        ESP_LOGW(TAG, "OLED init FAILED — diagnostic display unavailable");
    }
#endif

    // ── Gauge-specific servo range and damping ────────────────────────
    if (ROLE == LogRole::FUEL) {
        servo.setRange(0.0f, 100.0f);      // SOC 0–100%
        servo.setSmoothing(0.8f);           // slow — SOC changes gradually
    } else if (ROLE == LogRole::AMPS) {
        servo.setRange(-100.0f, 200.0f);   // -100A regen to 200A discharge
        servo.setSmoothing(0.3f);           // snappy — current changes fast
    } else if (ROLE == LogRole::TEMP) {
        servo.setRange(-10.0f, 50.0f);     // -10°C to 50°C
        servo.setSmoothing(1.0f);          // slow — temp changes very gradually
    }

    // ── Self-test at startup ─────────────────────────────────────────
#ifdef HAS_OLED
    diagState = STATE_TEST;
#endif
    runSelfTest();

#ifdef HAS_OLED
    // ── OLED self-test phase ──────────────────────────────────────────
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
    diagState = STATE_IDLE;
#endif

    canLog.log(LogLevel::LOG_INFO, LogEvent::BOOT_COMPLETE, millis());
    ESP_LOGI(TAG, "Init complete.");
}

void loop() {
    canBus.checkErrors();
    heartbeat.update();

    // ── CAN receive — drain queue ───────────────────────────────────
    uint32_t id;
    uint8_t data[8];
    uint8_t len;
    while (canBus.receive(id, data, len)) {
        lastCanRxMs = millis();
        canRxCount++;
        ESP_LOGD(TAG, "CAN RX: id=0x%03X len=%d data=%02X %02X %02X %02X %02X %02X %02X %02X",
                 id, len, data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7]);

        // ── On-demand self-test via CAN 0x730 ────────────────────────
        if (id == CAN_ID_SELF_TEST) {
            uint8_t target = data[0];
            if (target == SELF_TEST_TARGET_ALL ||
                target == static_cast<uint8_t>(LOG_ROLE)) {
                runSelfTest();
            }
        }

        // ── Gauge-specific Leaf CAN decode ───────────────────────────
        if (ROLE == LogRole::FUEL) {
            if (id == CAN_ID_LEAF_SOC_PRECISE) {
                // Primary: precise SOC from 0x55B
                gaugeValue = LeafCan::decodePreciseSOC(data);
                lastGaugeUpdateMs = millis();
            } else if (id == CAN_ID_LEAF_BATTERY_STATUS) {
                // Fallback: coarse SOC from 0x1DB if precise is stale
                if (millis() - lastGaugeUpdateMs > 1000) {
                    BatteryStatus bs = LeafCan::decodeBatteryStatus(data);
                    gaugeValue = bs.socPercent;
                    lastGaugeUpdateMs = millis();
                }
            }
        } else if (ROLE == LogRole::AMPS) {
            if (id == CAN_ID_LEAF_BATTERY_STATUS) {
                BatteryStatus bs = LeafCan::decodeBatteryStatus(data);
                gaugeValue = bs.currentA;
                lastGaugeUpdateMs = millis();
                if (fabsf(gaugeValue - lastLoggedGaugeValue) >= GAUGE_LOG_DEADBAND) {
                    ESP_LOGI(TAG, "Amps: %.1f A (was %.1f A)", gaugeValue, lastLoggedGaugeValue);
                    lastLoggedGaugeValue = gaugeValue;
                }
            }
        } else if (ROLE == LogRole::TEMP) {
            if (id == CAN_ID_LEAF_BATTERY_TEMP) {
                gaugeValue = (float)LeafCan::decodeBatteryTemp(data);
                lastGaugeUpdateMs = millis();
            }
        }

        // ── Common: body state flags (turn signals, hazards) ─────────
        if (id == CAN_ID_BODY_STATE) {
            lastBodyFlags = data[0];
        }

        // ── Common: ambient light level ──────────────────────────────
        if (id == CAN_ID_GPS_AMBIENT_LIGHT) {
            ledRing.setAmbientFromCategory(data[0]);
        }
    }

    // ── Update servo from gauge value ────────────────────────────────
    servo.setValue(gaugeValue);

    // ── Update LED ring warnings and animations ─────────────────────
    updateAnimations();
    updateWarnings();

    // ── CAN silence watchdog ────────────────────────────────────────
    unsigned long now = millis();
    bool canSilent = (now - lastCanRxMs) > CAN_SILENCE_TIMEOUT_MS && now > CAN_SILENCE_TIMEOUT_MS;

    if (canSilent && !canSilenceMode) {
        canSilenceMode = true;
        lastFaultProbeMs = now;
        ledRing.startBluePulse();
        canLog.log(LogLevel::LOG_WARN, LogEvent::CAN_SILENCE);
        ESP_LOGW(TAG, "CAN silence — entering fault mode");
    }

    if (canSilenceMode) {
        if (!canSilent) {
            // Traffic resumed — exit fault mode
            canSilenceMode = false;
            ledRing.stopBluePulse();
            canLog.log(LogLevel::LOG_INFO, LogEvent::BUS_RECOVERED);
            ESP_LOGI(TAG, "CAN traffic resumed");
        } else if ((now - lastFaultProbeMs) > FAULT_PROBE_INTERVAL_MS) {
            // Periodic probe: log status + attempt TWAI recovery
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

    ledRing.update();
    servo.update();

#ifdef HAS_OLED
    // ── State tracking ────────────────────────────────────────────────
    if (canRxCount > 0 && diagState == STATE_IDLE) {
        diagState = STATE_RUN;
    }
    if (canSilenceMode && diagState != STATE_ERR) {
        diagState = STATE_ERR;
    }
    if (!canSilenceMode && diagState == STATE_ERR) {
        diagState = STATE_RUN;
    }

    // ── OLED diagnostic refresh (4 Hz) ────────────────────────────────
    if (now - lastOledRefreshMs >= OLED_REFRESH_MS) {
        lastOledRefreshMs = now;
        oledDrawDiagnostics();
    }

    // ── Onboard LED heartbeat (1 Hz toggle) ───────────────────────────
    if (now - lastLedToggleMs >= 500) {
        lastLedToggleMs = now;
        onboardLedState = !onboardLedState;
        digitalWrite(PIN_ONBOARD_LED, onboardLedState ? HIGH : LOW);
    }
#endif
}
