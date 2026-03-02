# Body Controller ESP32 — GPIO Pinout

| GPIO | Define | Signal | Notes |
|-----:|--------|--------|-------|
| 12 | PIN_CAN_TX | CAN TX | TJA1050 |
| 25 | PIN_CAN_RX | CAN RX | TJA1050 |
| 35 | PIN_HALL_SENSOR | Driveshaft speed | INPUT_PULLUP, ISR FALLING, 2 magnets/rev |
| 23 | PIN_KEY_ON | Key On | Resistor divider, active-high |
| 22 | PIN_KEY_START | Key Start | Resistor divider, active-high |
| 21 | PIN_KEY_ACCESSORY | Key Accessory | Resistor divider, active-high |
| 19 | PIN_LEFT_TURN | Left Turn | Resistor divider, active-high |
| 18 | PIN_RIGHT_TURN | Right Turn | Resistor divider, active-high |
| 17 | PIN_HAZARD | Hazard Switch | Resistor divider, active-high |
| 4 | PIN_RUNNING_LIGHTS | Running Lights | Resistor divider, active-high |
| 32 | PIN_HEADLIGHTS | Headlights | Resistor divider, active-high |
| 26 | PIN_BRAKE | Brake | Resistor divider, active-high |
| 27 | PIN_REGEN | Regen Active | Resistor divider, active-high |
| 14 | PIN_FAN | Coolant Fan | Resistor divider, active-high |
| 16 | PIN_REVERSE | Reverse | Resistor divider, active-high |
| 5 | PIN_CHARGE_PORT | Charge Port Open | Resistor divider, active-high |

**16 GPIOs used** — 2 CAN, 1 hall sensor, 13 resistor-divider inputs from 12V signals.
