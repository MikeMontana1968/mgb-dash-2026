/**
 * MGB Dash 2026 — Synthetic demo data source (port of synthetic_source.py).
 *
 * 10 Hz setInterval. Same sinusoidal formulas as the Python version.
 * GPS heartbeat dropped during 45 < (t%90) < 65 to show staleness.
 */

// Heartbeat roles (trimmed names matching SIGNAL_GROUPS)
const ALL_ROLES = ["FUEL", "AMPS", "TEMP", "SPEED", "BODY", "DASH", "GPS"];

// Gear ratios for RPM calculation
const GEAR_RATIOS = { 1: 3.41, 2: 2.166, 3: 1.38, 4: 1.00 };
const DIFF = 3.909;
const TIRE = 26.5;
const RPM_BASE = 5280.0 * 12.0 / (60.0 * Math.PI * TIRE) * DIFF;

export class DemoSource {
    constructor(state) {
        this._state = state;
        this._timer = null;
        this._t = 0;
    }

    start() {
        this._t = 0;
        this._timer = setInterval(() => {
            this._tick();
            this._t += 0.1;  // 10 Hz
        }, 100);
    }

    stop() {
        if (this._timer !== null) {
            clearInterval(this._timer);
            this._timer = null;
        }
    }

    _tick() {
        const t = this._t;
        const speed = 30 + 15 * Math.sin(t * 0.2);
        let gear = this._gearFromSpeed(speed);

        // Periodically force wrong gear
        const cycle = Math.floor(t) % 40;
        if (cycle > 10 && cycle < 15 && gear > 1) gear -= 1;
        else if (cycle > 25 && cycle < 30 && gear < 4) gear += 1;

        this._emitLeafMotor(t, speed, gear);
        this._emitLeafBattery(t);
        this._emitLeafCharger(t);
        this._emitLeafTemps(t);
        this._emitLeafVcm();
        this._emitResolve(t);
        this._emitBody(t, speed, gear);
        this._emitGps(t);
        this._emitHeartbeats(t);
    }

    _gearFromSpeed(speed) {
        if (speed <= 1) return 0;
        return Math.min(4, Math.max(1, Math.floor(speed / 15) + 1));
    }

    _emitLeafMotor(t, speed, gear) {
        let rpm = 0;
        if (gear >= 1 && gear <= 4 && speed > 0.5) {
            const expected = speed * RPM_BASE * GEAR_RATIOS[gear];
            const drift = 1200 * Math.sin(t * 0.15);
            rpm = Math.max(0, Math.round(expected + drift));
        }
        const torque = 80 + 40 * Math.sin(t * 0.25);
        this._state.updateSignals({
            motor_rpm: rpm,
            available_torque_nm: Math.round(torque * 10) / 10,
            failsafe: 0,
        });
    }

    _emitLeafBattery(t) {
        const voltage = 360 + 10 * Math.sin(t * 0.05);
        const current = -30 + 25 * Math.sin(t * 0.2);
        const soc = 72 + 5 * Math.sin(t * 0.01);
        this._state.updateSignals({
            battery_voltage_v:   Math.round(voltage * 10) / 10,
            battery_current_a:   Math.round(current * 10) / 10,
            soc_percent:         Math.floor(soc),
            soc_precise_percent: Math.round((soc + 0.37) * 100) / 100,
            gids:                Math.floor(200 + 20 * Math.sin(t * 0.01)),
            soh_percent:         92,
            battery_temp_c:      Math.round((28 + 3 * Math.sin(t * 0.02)) * 10) / 10,
        });
    }

    _emitLeafCharger(t) {
        const power = 6.6 + 0.5 * Math.sin(t * 0.1);
        this._state.updateSignals({
            charge_power_kw: Math.round(power * 100) / 100,
        });
    }

    _emitLeafTemps(t) {
        // Periodically spike battery temp above 45C
        let battTemp;
        if ((t % 60) > 30 && (t % 60) < 40) {
            battTemp = 48.0;
        } else {
            battTemp = Math.round((28 + 3 * Math.sin(t * 0.02)) * 10) / 10;
        }
        this._state.updateSignals({
            motor_temp_c:    Math.round((45 + 10 * Math.sin(t * 0.03)) * 10) / 10,
            igbt_temp_c:     Math.round((42 + 8 * Math.sin(t * 0.025)) * 10) / 10,
            inverter_temp_c: Math.round((38 + 6 * Math.sin(t * 0.02)) * 10) / 10,
            battery_temp_c:  battTemp,
        });
    }

    _emitLeafVcm() {
        this._state.updateSignals({ main_relay_closed: true });
    }

    _emitResolve(t) {
        const gearVal = t > 5 ? 2 : 0;
        this._state.updateSignals({
            resolve_gear:           gearVal,
            resolve_ignition_on:    true,
            resolve_system_on:      true,
            resolve_regen_strength: Math.floor(50 + 30 * Math.sin(t * 0.4)),
            resolve_soc_percent:    Math.floor(72 + 5 * Math.sin(t * 0.01)),
        });
    }

    _emitBody(t, speed, gear) {
        let flags = 1; // KEY_ON
        if (speed > 1 && Math.sin(t * 0.5) > 0.7) flags |= 2;  // BRAKE
        if (speed > 10 && Math.sin(t * 0.3) > 0.8) flags |= 4;  // REGEN
        if (Math.floor(t) % 20 < 3) flags |= 32;                // LEFT_TURN

        this._state.updateSignals({
            key_on:         !!(flags & 1),
            brake:          !!(flags & 2),
            regen:          !!(flags & 4),
            reverse:        false,
            left_turn:      !!(flags & 32),
            right_turn:     false,
            body_speed_mph: Math.round(Math.max(0, speed) * 10) / 10,
            body_gear:      gear,
            odometer_miles: 12345 + Math.floor(t * Math.max(0, speed) / 3600),
        });
    }

    _emitGps(t) {
        const lat = 42.3601 + 0.001 * Math.sin(t * 0.01);
        const lon = -71.0589 + 0.001 * Math.cos(t * 0.01);
        const speed = 30 + 15 * Math.sin(t * 0.2);
        this._state.updateSignals({
            gps_speed_mph:      Math.round(Math.max(0, speed) * 10) / 10,
            gps_latitude:       Math.round(lat * 1000000) / 1000000,
            gps_longitude:      Math.round(lon * 1000000) / 1000000,
            gps_elevation_m:    Math.round((10 + 2 * Math.sin(t * 0.005)) * 10) / 10,
            gps_time_utc_s:     (t * 10) % 86400,
            ambient_light_name: "DAYLIGHT",
        });
    }

    _emitHeartbeats(t) {
        const counter = Math.floor(t) % 256;
        for (const role of ALL_ROLES) {
            // Drop GPS heartbeat periodically to show staleness
            if (role === "GPS" && (t % 90) > 45 && (t % 90) < 65) {
                continue;
            }
            this._state.updateHeartbeat(role, counter, 0);
        }
    }
}
