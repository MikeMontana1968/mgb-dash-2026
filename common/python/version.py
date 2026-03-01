"""
MGB Dash 2026 — Shared Version Module

Computes the project version string: ``milestone.YMMDD.githash``

Usage:
    from common.python.version import get_version
    version = get_version("GPS")   # -> "GPS v1.60228.a1b2c3d"
"""

import datetime
import os
import subprocess

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def get_version(role: str) -> str:
    """Return version string like ``GPS v1.60228.a1b2c3d``."""
    # Milestone
    version_file = os.path.join(_REPO_ROOT, "VERSION")
    with open(version_file) as f:
        milestone = f.read().strip()

    # YMMDD
    today = datetime.date.today()
    ymmdd = f"{today.year % 10}{today.month:02d}{today.day:02d}"

    # Short git hash
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_REPO_ROOT,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        git_hash = "unknown"

    return f"{role} v{milestone}.{ymmdd}.{git_hash}"
