/**
 * MGB Dash 2026 — DOM rendering for diagnostics PWA.
 *
 * Builds DOM once on init. 4 Hz render loop updates textContent +
 * className on stable elements. Temperature °F conversion in display
 * layer (same as diagnostics.py).
 */

// ── Signal groups — matches diagnostics.py SIGNAL_GROUPS exactly ──

const SIGNAL_GROUPS = [
    ["LEAF MOTOR", [
        ["motor_rpm",           "Motor RPM",    "RPM",  "1DA"],
        ["available_torque_nm", "Avail Torque",  "Nm",   "1DA"],
        ["failsafe",           "Failsafe",      "",     "1DA"],
    ]],
    ["LEAF BATTERY", [
        ["battery_voltage_v",   "Battery V",    "V",    "1DB"],
        ["battery_current_a",   "Battery A",    "A",    "1DB"],
        ["soc_percent",         "SOC",          "%",    "1DB"],
        ["soc_precise_percent", "SOC Precise",  "%",    "55B"],
        ["gids",                "GIDs",         "",     "5BC"],
        ["soh_percent",         "SOH",          "%",    "5BC"],
        ["battery_temp_c",      "Batt Temp",    "\u00b0F",   "5C0"],
    ]],
    ["LEAF CHARGER", [
        ["charge_power_kw", "Charge Power", "kW",  "1DC"],
    ]],
    ["LEAF TEMPS", [
        ["motor_temp_c",    "Motor Temp",    "\u00b0F",  "55A"],
        ["igbt_temp_c",     "IGBT Temp",     "\u00b0F",  "55A"],
        ["inverter_temp_c", "Inverter Temp", "\u00b0F",  "55A"],
    ]],
    ["LEAF VCM", [
        ["main_relay_closed", "Main Relay", "",  "390"],
    ]],
    ["RESOLVE", [
        ["resolve_gear",           "Gear",       "",   "539"],
        ["resolve_ignition_on",    "Ignition",   "",   "539"],
        ["resolve_system_on",      "System",     "",   "539"],
        ["resolve_regen_strength", "Regen Str",  "",   "539"],
        ["resolve_soc_percent",    "RSolve SOC", "%",  "539"],
    ]],
    ["BODY", [
        ["key_on",          "Key On",    "",    "710"],
        ["brake",           "Brake",     "",    "710"],
        ["regen",           "Regen",     "",    "710"],
        ["reverse",         "Reverse",   "",    "710"],
        ["left_turn",       "Left Turn", "",    "710"],
        ["body_speed_mph",  "Speed",     "mph", "711"],
        ["body_gear",       "Gear",      "",    "712"],
        ["odometer_miles",  "Odometer",  "mi",  "713"],
    ]],
    ["GPS", [
        ["gps_speed_mph",      "GPS Speed",  "mph", "720"],
        ["gps_latitude",       "Latitude",   "\u00b0",   "723"],
        ["gps_longitude",      "Longitude",  "\u00b0",   "724"],
        ["gps_elevation_m",    "Elevation",  "m",   "725"],
        ["gps_time_utc_s",     "Time UTC",   "s",   "721"],
        ["ambient_light_name", "Ambient",    "",    "726"],
    ]],
];

// Left column: LEAF groups (indices 0-4), Right column: RESOLVE/BODY/GPS (5-7)
const LEFT_GROUPS  = [0, 1, 2, 3, 4];
const RIGHT_GROUPS = [5, 6, 7];

// Heartbeat roles
const HB_ROLES = ["FUEL", "AMPS", "TEMP", "SPEED", "BODY", "DASH", "GPS"];

// Collapsed groups (persisted in this Set)
const collapsedGroups = new Set();

// DOM element cache — signal key → {ageEl, valEl}
const signalElements = new Map();
// Heartbeat DOM cache — role → {dotEl, uptimeEl}
const hbElements = new Map();
// Rate counter element
let msgRateEl = null;


// ── Freshness helpers ──────────────────────────────────────────────

function freshnessClass(ageSeconds) {
    if (ageSeconds < 2)   return "fresh";
    if (ageSeconds < 5)   return "aging";
    if (ageSeconds < 10)  return "stale";
    if (ageSeconds < 30)  return "dead";
    return "never";
}

function ageText(ageSeconds) {
    if (ageSeconds < 1)   return "\u2713";       // ✓
    if (ageSeconds < 100) return Math.floor(ageSeconds) + "s";
    return "---";
}

function ageClass(ageSeconds) {
    return ageSeconds < 1 ? "age-fresh" : "age-dim";
}

function formatValue(value, unit) {
    if (typeof value === "boolean") return value ? "ON" : "OFF";
    if (typeof value === "number") {
        if (unit === "\u00b0F") {
            // Convert C → F in display layer
            value = value * 9 / 5 + 32;
        }
        if (Number.isInteger(value)) return String(value);
        return value.toFixed(1);
    }
    return String(value);
}


// ── Build DOM (called once) ────────────────────────────────────────

export function buildUI() {
    const grid = document.getElementById("signal-grid");
    const container = document.createElement("div");
    container.className = "grid-container";

    const leftCol = document.createElement("div");
    leftCol.className = "grid-column";
    const rightCol = document.createElement("div");
    rightCol.className = "grid-column";

    for (const gi of LEFT_GROUPS) {
        leftCol.appendChild(buildGroup(gi));
    }
    for (const gi of RIGHT_GROUPS) {
        rightCol.appendChild(buildGroup(gi));
    }

    container.appendChild(leftCol);
    container.appendChild(rightCol);
    grid.appendChild(container);

    // Heartbeat bar
    buildHeartbeatBar();

    // Cache rate element
    msgRateEl = document.getElementById("msg-rate");
}

function buildGroup(gi) {
    const [groupName, signals] = SIGNAL_GROUPS[gi];

    const card = document.createElement("div");
    card.className = "signal-group";
    card.dataset.group = gi;

    // Header
    const header = document.createElement("div");
    header.className = "group-header";
    header.innerHTML = `<span class="chevron">\u25BC</span><span class="group-name">${groupName}</span>`;
    header.addEventListener("click", () => {
        if (collapsedGroups.has(gi)) {
            collapsedGroups.delete(gi);
            card.classList.remove("collapsed");
        } else {
            collapsedGroups.add(gi);
            card.classList.add("collapsed");
        }
    });

    // Body
    const body = document.createElement("div");
    body.className = "group-body";

    for (const [sigKey, label, unit, canId] of signals) {
        const row = document.createElement("div");
        row.className = "signal-row";

        const canEl = document.createElement("span");
        canEl.className = "sig-can";
        canEl.textContent = canId;

        const ageEl = document.createElement("span");
        ageEl.className = "sig-age age-dim";
        ageEl.textContent = "---";

        const valEl = document.createElement("span");
        valEl.className = "sig-val never";
        valEl.textContent = "---";

        const lblEl = document.createElement("span");
        lblEl.className = "sig-label";
        lblEl.textContent = label;

        row.appendChild(canEl);
        row.appendChild(ageEl);
        row.appendChild(valEl);
        row.appendChild(lblEl);
        body.appendChild(row);

        // Cache for fast updates
        signalElements.set(sigKey, { ageEl, valEl, unit });
    }

    card.appendChild(header);
    card.appendChild(body);
    return card;
}

function buildHeartbeatBar() {
    const bar = document.getElementById("heartbeat-bar");
    for (const role of HB_ROLES) {
        const slot = document.createElement("div");
        slot.className = "hb-slot";

        const dotRow = document.createElement("div");
        dotRow.className = "hb-dot-row";

        const dot = document.createElement("div");
        dot.className = "hb-dot never";

        const label = document.createElement("span");
        label.className = "hb-label";
        label.textContent = role;

        dotRow.appendChild(dot);
        dotRow.appendChild(label);

        const uptime = document.createElement("div");
        uptime.className = "hb-uptime";
        uptime.textContent = "---";

        slot.appendChild(dotRow);
        slot.appendChild(uptime);
        bar.appendChild(slot);

        hbElements.set(role, { dotEl: dot, uptimeEl: uptime });
    }
}


// ── Render update (called at 4 Hz) ────────────────────────────────

export function updateUI(state) {
    const signals = state.getAllSignals();
    const heartbeats = state.getHeartbeats();

    // Update signal rows
    for (const [sigKey, els] of signalElements) {
        const sv = signals.get(sigKey);
        if (!sv) {
            els.ageEl.textContent = "---";
            els.ageEl.className = "sig-age age-dim";
            els.valEl.textContent = "---";
            els.valEl.className = "sig-val never";
            continue;
        }

        const age = sv.ageSeconds;

        // Age cell
        els.ageEl.textContent = ageText(age);
        els.ageEl.className = "sig-age " + ageClass(age);

        // Value cell
        const valStr = formatValue(sv.value, els.unit);
        els.valEl.textContent = valStr.substring(0, 8);
        els.valEl.className = "sig-val " + freshnessClass(age);
    }

    // Update heartbeat dots
    for (const [role, els] of hbElements) {
        const hb = heartbeats.get(role);
        if (!hb) {
            els.dotEl.className = "hb-dot never";
            els.uptimeEl.textContent = "---";
            continue;
        }
        const age = hb.ageSeconds;
        els.dotEl.className = "hb-dot " + freshnessClass(age);
        els.uptimeEl.textContent = hb.counter;
    }

    // Update message rate
    if (msgRateEl) {
        msgRateEl.textContent = `msgs: ${state.messagesPerSec}/s`;
    }
}
