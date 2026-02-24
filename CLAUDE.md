# MGB Dash 2026 — Project Instructions

## Code Generation

`common/can_ids.json` is the **single source of truth** for all CAN message definitions.

After editing `common/can_ids.json`, always run the code generator to update derived files:

```powershell
python tools/codegen.py
```

This regenerates:
- `common/python/can_ids.py`
- `common/python/leaf_messages.py`
- `common/python/resolve_messages.py`

Do NOT edit these generated files by hand — changes will be overwritten.

## Build

- ESP32 firmware: `cd firmware && pio run`
- Python packages use `uv` + `pyproject.toml` (no requirements.txt)
