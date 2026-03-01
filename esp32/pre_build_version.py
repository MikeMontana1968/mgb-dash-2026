"""
PlatformIO pre-build script — inject version defines into all ESP32 builds.

Reads VERSION file (milestone), computes YMMDD from today's date, gets short
git hash, and passes them as -D compiler flags.

Output defines:
    VERSION_MILESTONE  (int)    e.g. 1
    VERSION_DATE       (string) e.g. "60228"
    VERSION_HASH       (string) e.g. "a1b2c3d"
"""

import subprocess
import datetime
import os

Import("env")  # noqa: F821 — PlatformIO magic

# ── Read milestone from VERSION file ─────────────────────────────────
version_file = os.path.join(env.subst("$PROJECT_DIR"), "..", "VERSION")
with open(version_file) as f:
    milestone = f.read().strip()

# ── Compute YMMDD ────────────────────────────────────────────────────
today = datetime.date.today()
ymmdd = f"{today.year % 10}{today.month:02d}{today.day:02d}"

# ── Get short git hash ───────────────────────────────────────────────
try:
    git_hash = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=os.path.join(env.subst("$PROJECT_DIR"), ".."),
        stderr=subprocess.DEVNULL,
    ).decode().strip()
except Exception:
    git_hash = "unknown"

# ── Inject as build flags ────────────────────────────────────────────
env.Append(CPPDEFINES=[
    ("VERSION_MILESTONE", int(milestone)),
    ("VERSION_DATE", env.StringifyMacro(ymmdd)),
    ("VERSION_HASH", env.StringifyMacro(git_hash)),
])

print(f"[VERSION] {milestone}.{ymmdd}.{git_hash}")
