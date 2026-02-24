"""MGB Dash 2026 — Context state machine for display switching."""


class ContextManager:
    """Manages active display context and auto-transition rules.

    Auto-transitions are skipped while in Diagnostics.
    """

    def __init__(self, contexts: dict, initial: str = "diagnostics"):
        self._contexts = contexts
        self._active_name = initial
        self._previous_name = initial
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
        # Future auto-transitions:
        # - Startup -> Idle: after 3s or first CAN message
        # - Idle <-> Driving: speed > 1 mph / speed = 0 for 10s
        # - Idle <-> Charging: charge_power > 0.5 kW / charge = 0 for 5s
