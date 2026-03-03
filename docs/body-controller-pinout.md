# Body Controller ESP32 — GPIO Pinout

Confirmed via bench testing 2026-03-03.

| GPIO | Define | Signal | Notes |
|-----:|--------|--------|-------|
| 12 | PIN_CAN_TX | CAN TX | TJA1050 |
| 25 | PIN_CAN_RX | CAN RX | TJA1050 |
| 35 | PIN_HALL_SENSOR | Driveshaft speed | INPUT_PULLUP, ISR FALLING, 2 magnets/rev |
| 23 | PIN_BRAKE | Brake | Resistor divider, active-high |
| 22 | PIN_REVERSE | Reverse | Resistor divider, active-high |
| 21 | PIN_REGEN | Regen Active | Resistor divider, active-high |
| 27 | PIN_LEFT_TURN | Left Turn | Resistor divider, active-high |
| 18 | PIN_RIGHT_TURN | Right Turn | Resistor divider, active-high |

**8 GPIOs used** — 2 CAN, 1 hall sensor, 5 resistor-divider inputs from 12V signals.

### Not wired this iteration

These signals exist in the CAN protocol (flag bits reserved) but are not physically wired yet:

- KEY_ON, KEY_START, KEY_ACCESSORY
- HAZARD (dedicated input — timing-based detection from LEFT+RIGHT is active)
- RUNNING_LIGHTS, HEADLIGHTS
- FAN, CHARGE_PORT
