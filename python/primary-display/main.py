"""
MGB Dash 2026 — Primary Display (Pi 4B)

pycairo + pygame dashboard on Waveshare 3.4" Round DSI LCD (800x800).
Reads CAN bus (or synthetic/replay data), drives context-based display.

Usage:
    python main.py                                        # synthetic, all_signals
    python main.py --source synthetic --scenario driving   # driving scenario
    python main.py --source replay --file session.asc      # replay (Phase 3)
    python main.py --source can                            # real CAN (Phase 4)
    python main.py --context diagnostics                   # force initial context
"""

import sys
import os
import argparse

# Add repo root so common.python imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.python.log_setup import setup_logging
from common.python.version import get_version

logger = setup_logging("dash")


def main():
    parser = argparse.ArgumentParser(description="MGB Dash 2026 — Primary Display")
    parser.add_argument(
        "--source", choices=["synthetic", "replay", "can"],
        default="synthetic", help="Data source type"
    )
    parser.add_argument(
        "--scenario", default="all_signals",
        help="Synthetic scenario: all_signals, idle, driving, charging"
    )
    parser.add_argument(
        "--speed", type=float, default=1.0,
        help="Replay/synthetic speed multiplier"
    )
    parser.add_argument("--file", help="Replay log file path")
    parser.add_argument(
        "--context", default="diagnostics",
        help="Initial display context"
    )
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=800)
    args = parser.parse_args()

    version = get_version("DASH")
    logger.critical("%s starting...", version)
    logger.info("Source: %s  Scenario: %s  Speed: %.1fx",
                args.source, args.scenario, args.speed)

    # ── Data model + alert manager ────────────────────────────────────
    from vehicle_state import VehicleState
    from contexts.alerts import AlertManager
    state = VehicleState()
    state.alert_manager = AlertManager()

    # ── Data source ──────────────────────────────────────────────────
    if args.source == "synthetic":
        from data_sources.synthetic_source import SyntheticSource
        source = SyntheticSource(
            state, scenario=args.scenario, speed_factor=args.speed
        )
    elif args.source == "replay":
        raise NotImplementedError("Replay source not yet implemented (Phase 3)")
    elif args.source == "can":
        from data_sources.can_source import CanBusSource
        source = CanBusSource(state)

    # ── Contexts ─────────────────────────────────────────────────────
    from contexts.diagnostics import DiagnosticsContext
    from contexts.driving import DrivingContext
    from contexts.idle import IdleContext
    from contexts.charging import ChargingContext
    from contexts.startup import StartupContext
    from contexts.context_manager import ContextManager

    diag = DiagnosticsContext()
    diag.set_source_label(args.source)
    contexts = {
        "startup":     StartupContext(),
        "driving":     DrivingContext(),
        "idle":        IdleContext(),
        "charging":    ChargingContext(),
        "diagnostics": diag,
    }
    cm = ContextManager(contexts, initial=args.context)

    # ── Shift advisor ──────────────────────────────────────────────
    from shift_advisor import ShiftAdvisor
    shift = ShiftAdvisor()

    # ── Display engine ───────────────────────────────────────────────
    from display_engine import DisplayEngine
    engine = DisplayEngine(cm, state, shift_advisor=shift,
                           width=args.width, height=args.height)

    # ── Run ──────────────────────────────────────────────────────────
    source.start()
    logger.info("Data source started (%s)", args.source)

    try:
        engine.run()   # blocks until ESC / window close
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        source.stop()
        logger.info("Primary display stopped")


if __name__ == "__main__":
    main()
