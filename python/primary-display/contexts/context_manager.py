"""MGB Dash 2026 — Context state machine for display switching."""

import time


class ContextManager:
    """Manages active display context and auto-transition rules.

    Auto-transitions are skipped while in Diagnostics.
    Transition timers prevent jitter (require condition to hold for N seconds).
    """

    def __init__(self, contexts: dict, initial: str = "diagnostics"):
        self._contexts = contexts
        self._active_name = initial
        # Avoid _previous == _active (toggle_diagnostics would be a no-op)
        self._previous_name = "idle" if initial == "diagnostics" else initial
        # Transition timers: key → monotonic time when condition first became true
        self._timers: dict[str, float] = {}
        if initial in self._contexts:
            self._contexts[initial].on_enter(None)

    @property
    def active(self):
        return self._contexts[self._active_name]

    @property
    def active_name(self) -> str:
        return self._active_name

    def switch_to(self, name: str, state=None):
        if name not in self._contexts or name == self._active_name:
            return
        self.active.on_exit()
        self._previous_name = self._active_name
        self._active_name = name
        self._timers.clear()
        # Tell diagnostics which context to return to
        new_ctx = self._contexts[name]
        if hasattr(new_ctx, "set_previous_context"):
            new_ctx.set_previous_context(self._previous_name)
        new_ctx.on_enter(state)

    def toggle_diagnostics(self, state=None):
        if self._active_name == "diagnostics":
            self.switch_to(self._previous_name, state)
        else:
            self.switch_to("diagnostics", state)

    def evaluate(self, state):
        """Check auto-transition rules. Skipped in Diagnostics."""
        if self._active_name == "diagnostics":
            return

        signals = state.get_all_signals()

        speed_sv  = signals.get("body_speed_mph")
        charge_sv = signals.get("charge_power_kw")

        speed = speed_sv.value if speed_sv else 0.0
        charge_kw = charge_sv.value if charge_sv else 0.0

        active = self._active_name

        # ── Startup → Idle: after splash duration ─────────────────────
        if active == "startup":
            ctx = self._contexts.get("startup")
            if ctx and hasattr(ctx, "ready_to_leave") and ctx.ready_to_leave:
                self.switch_to("idle", state)
            return

        # ── Speed > 1 mph for 2s → Driving ───────────────────────────
        if active != "driving" and speed > 1.0:
            if self._timer_elapsed("to_driving", 2.0):
                self.switch_to("driving", state)
                return
        else:
            self._timer_reset("to_driving")

        # ── Speed = 0 for 10s → Idle (from driving) ──────────────────
        if active == "driving" and speed <= 0.5:
            if self._timer_elapsed("to_idle", 10.0):
                self.switch_to("idle", state)
                return
        else:
            self._timer_reset("to_idle")

        # ── Charge power > 0.5 kW for 3s → Charging ──────────────────
        if active != "charging" and charge_kw > 0.5:
            if self._timer_elapsed("to_charging", 3.0):
                self.switch_to("charging", state)
                return
        else:
            self._timer_reset("to_charging")

        # ── Charge stopped for 5s + speed = 0 → Idle (from charging) ─
        if active == "charging" and charge_kw < 0.1 and speed <= 0.5:
            if self._timer_elapsed("charge_to_idle", 5.0):
                self.switch_to("idle", state)
                return
        else:
            self._timer_reset("charge_to_idle")

    # ── Timer helpers ─────────────────────────────────────────────────

    def _timer_elapsed(self, key: str, duration: float) -> bool:
        """Return True if condition has been continuously true for `duration` seconds."""
        now = time.monotonic()
        if key not in self._timers:
            self._timers[key] = now
        return (now - self._timers[key]) >= duration

    def _timer_reset(self, key: str):
        """Reset a transition timer."""
        self._timers.pop(key, None)
