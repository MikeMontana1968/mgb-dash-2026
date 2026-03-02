/**
 * MGB Dash 2026 — Vehicle state store (port of vehicle_state.py).
 *
 * Uses performance.now() for monotonic timestamps. No locking needed
 * (JS is single-threaded). All times in milliseconds internally,
 * age_seconds properties convert for display.
 */

export class SignalValue {
    constructor(value) {
        this.value = value;
        this.timestamp = performance.now();
    }

    get ageSeconds() {
        return (performance.now() - this.timestamp) / 1000;
    }
}

export class HeartbeatInfo {
    constructor(role, counter, errorFlags) {
        this.role = role;
        this.counter = counter;
        this.errorFlags = errorFlags;
        this.timestamp = performance.now();
    }

    get ageSeconds() {
        return (performance.now() - this.timestamp) / 1000;
    }
}

export class VehicleState {
    constructor() {
        this._signals = new Map();
        this._heartbeats = new Map();
        this._messageCount = 0;
        this._rateWindowStart = performance.now();
        this._rateWindowCount = 0;
        this._messagesPerSec = 0;
    }

    updateSignals(decoded) {
        const now = performance.now();
        for (const [key, value] of Object.entries(decoded)) {
            const sv = new SignalValue(value);
            sv.timestamp = now;
            this._signals.set(key, sv);
        }
        this._tickRate();
    }

    updateHeartbeat(role, counter, errorFlags) {
        this._heartbeats.set(role, new HeartbeatInfo(role, counter, errorFlags));
        this._tickRate();
    }

    getSignal(key) {
        return this._signals.get(key) || null;
    }

    getAllSignals() {
        return this._signals;
    }

    getHeartbeats() {
        return this._heartbeats;
    }

    get messagesPerSec() {
        return this._messagesPerSec;
    }

    _tickRate() {
        this._rateWindowCount++;
        const now = performance.now();
        const elapsed = now - this._rateWindowStart;
        if (elapsed >= 1000) {
            this._messagesPerSec = Math.round(this._rateWindowCount / (elapsed / 1000));
            this._rateWindowStart = now;
            this._rateWindowCount = 0;
        }
    }
}
