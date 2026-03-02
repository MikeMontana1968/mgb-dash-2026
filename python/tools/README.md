# Diagnostic Tools

CLI Python tools for CAN bus testing and diagnostics. Designed to run on a dedicated bench Pi (or any machine with an Innomaker USB2CAN adapter).

## Components

| Component | Part / Model | Interface | Connection | Notes |
|-----------|-------------|-----------|------------|-------|
| SBC | Raspberry Pi 3B+ or 4B | — | — | Any model with USB |
| CAN Adapter | Innomaker USB2CAN | USB | USB-A port | gs_usb driver, SocketCAN |

> **No GPIO pins consumed.** CAN adapter is USB. No display needed — all tools are CLI.

## Tools

| Script | Description |
|--------|-------------|
| `can_monitor.py` | Decoded CAN traffic viewer — shows live messages with field names and values |
| `can_emulate.py` | Module emulator — pretends to be one or more dashboard modules on the bus |
| `can_inject.py` | Send a single CAN frame — quick one-shot message for testing |
| `can_replay.py` | Record and replay CAN bus sessions — capture traffic to file and play back |
| `can_stress.py` | Bus load testing — flood the bus to measure throughput and error rates |
| `can_cell_query.py` | Leaf battery cell voltage/shunt query via UDS (0x79B/0x7BB) |
| `can_scan.py` | Bus discovery and module detection — find active CAN IDs and heartbeats |
| `codegen.py` | Code generator — regenerates Python modules from `common/can_ids.json` |

> All tool scripts are currently stubs (argparse scaffolding only, no python-can integration yet) except `codegen.py` which is fully functional.

## Run

```bash
python python/tools/can_monitor.py --interface can0
python python/tools/can_inject.py --id 0x730 --data FF
```

## Setup

See [`pi-setup/test-monitor.sh`](../../pi-setup/test-monitor.sh) for bench Pi provisioning.
