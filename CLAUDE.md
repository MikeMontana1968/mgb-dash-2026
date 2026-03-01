# MGB Dash 2026 — Project Instructions

## Code Generation

`common/can_ids.json` is the **single source of truth** for all CAN message definitions.

After editing `common/can_ids.json`, always run the code generator to update derived files:

```powershell
python python/tools/codegen.py
```

This regenerates:
- `common/python/can_ids.py`
- `common/python/leaf_messages.py`
- `common/python/resolve_messages.py`

Do NOT edit these generated files by hand — changes will be overwritten.

## Versioning

All components use the same version scheme: **`milestone.YMMDD.githash`**

- `milestone` — manually bumped integer in `VERSION` file at repo root
- `YMMDD` — build date: single-digit year + 2-digit month + 2-digit day (e.g., `60228` = 2026-02-28)
- `githash` — short git hash at build time

Example: `3.60228.a1b2c3d`

Rules:
- Every component must log startup as a CRITICAL event, with the version number in the log body
- Version is for logging/diagnostics only — not included in heartbeat payload
- The `VERSION` file is the single source for the milestone number

## Build

- ESP32 firmware: `cd esp32 && pio run`
- Python packages use `uv` + `pyproject.toml` (no requirements.txt)
