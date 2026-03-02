/**
 * MGB Dash 2026 — CAN frame decoder (port of base.py _decode_and_store).
 *
 * Decodes raw CAN frames (arb_id + 8 data bytes) into named signals
 * and stores them in VehicleState.
 */

// ── CAN IDs ────────────────────────────────────────────────────────

// Leaf EV-CAN
const ID_1DA = 0x1DA;
const ID_1DB = 0x1DB;
const ID_1DC = 0x1DC;
const ID_390 = 0x390;
const ID_55A = 0x55A;
const ID_55B = 0x55B;
const ID_5BC = 0x5BC;
const ID_5C0 = 0x5C0;

// Resolve
const ID_539 = 0x539;

// Custom
const ID_HEARTBEAT     = 0x700;
const ID_BODY_STATE    = 0x710;
const ID_BODY_SPEED    = 0x711;
const ID_BODY_GEAR     = 0x712;
const ID_BODY_ODOMETER = 0x713;
const ID_GPS_SPEED     = 0x720;
const ID_GPS_TIME      = 0x721;
const ID_GPS_DATE      = 0x722;
const ID_GPS_LATITUDE  = 0x723;
const ID_GPS_LONGITUDE = 0x724;
const ID_GPS_ELEVATION = 0x725;
const ID_GPS_AMBIENT   = 0x726;
const ID_GPS_UTC_OFF   = 0x727;

// Body flag bits (byte 0)
const FLAG_KEY_ON     = 1 << 0;
const FLAG_BRAKE      = 1 << 1;
const FLAG_REGEN      = 1 << 2;
const FLAG_FAN        = 1 << 3;
const FLAG_REVERSE    = 1 << 4;
const FLAG_LEFT_TURN  = 1 << 5;
const FLAG_RIGHT_TURN = 1 << 6;
const FLAG_HAZARD     = 1 << 7;

// Ambient light names
const AMBIENT_NAMES = {
    0: "DAYLIGHT",
    1: "EARLY_TWILIGHT",
    2: "LATE_TWILIGHT",
    3: "DARKNESS",
};

// GPS double IDs → signal key
const GPS_DOUBLES = {
    [ID_GPS_SPEED]:     "gps_speed_mph",
    [ID_GPS_TIME]:      "gps_time_utc_s",
    [ID_GPS_DATE]:      "gps_date_days",
    [ID_GPS_LATITUDE]:  "gps_latitude",
    [ID_GPS_LONGITUDE]: "gps_longitude",
    [ID_GPS_ELEVATION]: "gps_elevation_m",
};


// ── Leaf decoders (port of leaf_messages.py) ───────────────────────

function decode1DA(d) {
    // Motor RPM: bytes 1-2, big-endian signed
    const rpm = (d[1] << 8 | d[2]);
    const rpmSigned = rpm > 32767 ? rpm - 65536 : rpm;
    // Available torque: bytes 3-4 upper 10 bits
    const torqueRaw = (d[3] << 8 | d[4]) >> 6;
    const torque = torqueRaw * 0.5 - 400;
    // Failsafe: byte 6 bits 2-3
    const failsafe = (d[6] >> 2) & 0x03;
    return { motor_rpm: rpmSigned, available_torque_nm: torque, failsafe };
}

function decode1DB(d) {
    const vRaw = (d[0] << 8 | d[1]) >> 6;
    const voltage = vRaw * 0.5;
    let cRaw = (d[2] << 8 | d[3]) >> 5;
    if (cRaw & 0x400) cRaw -= 0x800;
    const current = cRaw * 0.5;
    return { battery_voltage_v: voltage, battery_current_a: current, soc_percent: d[4] };
}

function decode1DC(d) {
    const pRaw = (d[0] << 8 | d[1]) >> 6;
    return { charge_power_kw: pRaw * 0.25 };
}

function decode390(d) {
    return { main_relay_closed: !!(d[4] & 1) };
}

function decode55A(d) {
    return {
        motor_temp_c: d[0] * 0.5,
        igbt_temp_c: d[1] * 0.5,
        inverter_temp_c: d[2] * 0.5,
    };
}

function decode55B(d) {
    const raw = (d[0] << 8) | d[1];
    return { soc_precise_percent: raw * 0.01 };
}

function decode5BC(d) {
    return {
        gids: (d[0] << 8 | d[1]) >> 6,
        soh_percent: (d[4] >> 1) & 0x7F,
    };
}

function decode5C0(d) {
    let raw = d[0];
    if (raw > 127) raw -= 256;
    return { battery_temp_c: raw - 40 };
}

// Leaf decoder dispatch
const LEAF_DECODERS = {
    [ID_1DA]: decode1DA,
    [ID_1DB]: decode1DB,
    [ID_1DC]: decode1DC,
    [ID_390]: decode390,
    [ID_55A]: decode55A,
    [ID_55B]: decode55B,
    [ID_5BC]: decode5BC,
    [ID_5C0]: decode5C0,
};


// ── Resolve decoder (port of resolve_messages.py) ──────────────────

function decode539(d) {
    return {
        resolve_gear:           d[0] & 0x0F,
        resolve_ignition_on:    !!(d[0] & (1 << 4)),
        resolve_system_on:      !!(d[0] & (1 << 5)),
        resolve_regen_strength: d[1],
        resolve_soc_percent:    d[2],
    };
}


/**
 * Decode a raw CAN frame and store results in VehicleState.
 * @param {VehicleState} state
 * @param {number} arbId - CAN arbitration ID
 * @param {Uint8Array} data - 8-byte payload
 */
export function decodeAndStore(state, arbId, data) {
    // Leaf EV-CAN
    if (arbId in LEAF_DECODERS) {
        state.updateSignals(LEAF_DECODERS[arbId](data));
        return;
    }

    // Resolve
    if (arbId === ID_539) {
        state.updateSignals(decode539(data));
        return;
    }

    // Heartbeat
    if (arbId === ID_HEARTBEAT) {
        let role = "";
        for (let i = 0; i < 5; i++) {
            role += String.fromCharCode(data[i]);
        }
        role = role.trim();
        state.updateHeartbeat(role, data[5], data[6]);
        return;
    }

    // Body state flags
    if (arbId === ID_BODY_STATE) {
        const f = data[0];
        state.updateSignals({
            key_on:     !!(f & FLAG_KEY_ON),
            brake:      !!(f & FLAG_BRAKE),
            regen:      !!(f & FLAG_REGEN),
            fan:        !!(f & FLAG_FAN),
            reverse:    !!(f & FLAG_REVERSE),
            left_turn:  !!(f & FLAG_LEFT_TURN),
            right_turn: !!(f & FLAG_RIGHT_TURN),
            hazard:     !!(f & FLAG_HAZARD),
        });
        return;
    }

    // Body speed (64-bit LE double)
    if (arbId === ID_BODY_SPEED) {
        const dv = new DataView(data.buffer, data.byteOffset, 8);
        state.updateSignals({ body_speed_mph: dv.getFloat64(0, true) });
        return;
    }

    // Body gear
    if (arbId === ID_BODY_GEAR) {
        state.updateSignals({ body_gear: data[0], body_reverse: !!data[1] });
        return;
    }

    // Body odometer (32-bit LE unsigned)
    if (arbId === ID_BODY_ODOMETER) {
        const dv = new DataView(data.buffer, data.byteOffset, 4);
        state.updateSignals({ odometer_miles: dv.getUint32(0, true) });
        return;
    }

    // GPS doubles
    if (arbId in GPS_DOUBLES) {
        const dv = new DataView(data.buffer, data.byteOffset, 8);
        state.updateSignals({ [GPS_DOUBLES[arbId]]: dv.getFloat64(0, true) });
        return;
    }

    // GPS ambient light
    if (arbId === ID_GPS_AMBIENT) {
        const cat = data[0];
        state.updateSignals({
            ambient_light: cat,
            ambient_light_name: AMBIENT_NAMES[cat] || `UNKNOWN(${cat})`,
        });
        return;
    }

    // GPS UTC offset (int16 LE signed)
    if (arbId === ID_GPS_UTC_OFF) {
        const dv = new DataView(data.buffer, data.byteOffset, 2);
        state.updateSignals({ gps_utc_offset_min: dv.getInt16(0, true) });
        return;
    }
}
