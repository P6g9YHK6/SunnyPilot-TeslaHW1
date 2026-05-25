# CAN HTTP API

HTTP API for sending known (DBC-defined) and raw CAN signals using existing openpilot infrastructure.

## Enable/Disable

Toggle in **Developer Settings** → "Enable CAN API (HTTP)". Only available while offroad. The toggle starts/stops the daemon via the process manager.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/status` | Car fingerprint, DBC loaded, API state |
| `GET` | `/api/v1/signals` | List all DBC messages and signals for the current car |
| `POST` | `/api/v1/signals/{name}` | Send one known signal: `{"values": {"signalName": value}, "bus": 0}` |
| `POST` | `/api/v1/signals/batch` | Send multiple: `[{"message": "MSG", "values": {...}}, ...]` |
| `POST` | `/api/v1/can/send` | Send raw CAN: `{"address": 1234, "data": "aabbccdd", "bus": 0}` |
| `GET` | `/openapi.json` | Dynamic OpenAPI 3.0.3 spec (auto-generated from DBC) |
| `GET` | `/docs` | Swagger UI |

## How it works

- Uses `PubMaster('sendcan')` — same ZMQ topic as `card.py` for injecting CAN frames
- DBC is loaded dynamically from `CarParamsCache` → `PLATFORMS[carFingerprint]`
- Known signals are encoded with `CANPacker.make_can_msg()` — respects checksums and counters
- The panda's safety model is **not bypassed** — the panda firmware still enforces safety

## Architecture

```
Client → HTTP :8700 (aiohttp) → PubMaster('sendcan') → pandad → Panda → CAN bus
```

Swagger UI is served from a CDN; the spec at `/openapi.json` is dynamically regenerated each request from the DBC for the currently fingerprinted car.
