/**
 * MGB Dash 2026 — Phone Diagnostics PWA entry point.
 *
 * Initializes state, builds UI, starts demo mode by default.
 * Mode buttons switch between DEMO and BLE sources.
 * 4 Hz render loop updates all signal/heartbeat DOM elements.
 */

import { VehicleState } from "./vehicle-state.js";
import { DemoSource } from "./demo-source.js";
import { BleSource } from "./ble-source.js";
import { buildUI, updateUI } from "./ui.js";

const state = new VehicleState();
const demoSource = new DemoSource(state);
const bleSource = new BleSource(state);

let activeMode = null;  // "demo" | "ble"
let renderTimer = null;

// ── Mode switching ─────────────────────────────────────────────────

function setMode(mode) {
    // Stop current source
    if (activeMode === "demo") demoSource.stop();
    if (activeMode === "ble")  bleSource.disconnect();

    activeMode = mode;

    // Update button highlight
    document.getElementById("btn-demo").classList.toggle("active", mode === "demo");
    document.getElementById("btn-ble").classList.toggle("active", mode === "ble");

    // Hide BLE status overlay
    const bleStatus = document.getElementById("ble-status");
    bleStatus.classList.remove("visible");

    if (mode === "demo") {
        demoSource.start();
    } else if (mode === "ble") {
        startBle();
    }
}

async function startBle() {
    const bleStatus = document.getElementById("ble-status");
    const bleMsg = document.getElementById("ble-msg");
    bleStatus.classList.add("visible");

    bleSource.onStatus = (msg) => {
        bleMsg.textContent = msg;
    };

    const ok = await bleSource.connect();
    if (ok) {
        // Hide overlay after successful connect
        setTimeout(() => bleStatus.classList.remove("visible"), 1500);
    }
}

// ── Render loop ────────────────────────────────────────────────────

function startRenderLoop() {
    renderTimer = setInterval(() => updateUI(state), 250);  // 4 Hz
}

// ── Init ───────────────────────────────────────────────────────────

function init() {
    buildUI();

    // Wire mode buttons
    document.getElementById("btn-demo").addEventListener("click", () => setMode("demo"));
    document.getElementById("btn-ble").addEventListener("click", () => setMode("ble"));

    // BLE overlay dismiss
    document.getElementById("ble-dismiss").addEventListener("click", () => {
        document.getElementById("ble-status").classList.remove("visible");
        if (!bleSource.connected) {
            setMode("demo");
        }
    });

    // Start render loop
    startRenderLoop();

    // Default to demo mode
    setMode("demo");
}

// Register service worker
if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
}

// Boot
document.addEventListener("DOMContentLoaded", init);
