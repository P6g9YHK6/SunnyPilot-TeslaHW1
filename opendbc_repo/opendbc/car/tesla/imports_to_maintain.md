# Tesla HW1 - Imports to Maintain

This file tracks all changes from [xnor-tech](https://github.com/xnor-tech) that must be preserved when merging upstream updates, as well as StarPilot-specific fixes.

## Last Synced

| Repository | Branch | Commit | Date | Notes |
|------------|--------|--------|------|-------|
| xnor-tech/opendbc | `master-xnor` | `6ea3718` (Tesla legacy) + `49da64f` (radar fix) | 2026-04-29 | Full audit completed |
| xnor-tech/panda | `master-xnor` | `56920ec` | 2026-04-29 | Ignition detection |
| xnor-tech/openpilot | `xnor-dev` | `eae878d` | 2026-04-29 | Minimal changes (card.py num_pandas) |

> Update these dates whenever a new upstream sync is performed.

## Source Repositories

| Repository | Branch | Purpose |
|------------|--------|---------|
| [xnor-tech/opendbc](https://github.com/xnor-tech/opendbc) | `master-xnor` | Car interface, DBC files, safety modes |
| [xnor-tech/panda](https://github.com/xnor-tech/panda) | `master-xnor` | Firmware, ignition detection, safety hooks |
| [xnor-tech/openpilot](https://github.com/xnor-tech/openpilot) | `xnor-dev` | Openpilot integration (minimal changes) |

---

## Key Commits to Track

### opendbc

| Commit | Description | Files Changed |
|--------|-------------|---------------|
| `6ea3718` | Tesla legacy & MG support, external panda integration | 34 files |
| `49da64f` | Fix Tesla 8Hz radar bug | `radar_interface.py` |
| `c954f40` | Tesla: return None from radar interface when no trigger | `radar_interface.py` |
| `37c8ae0` | Include all v1 body addresses in fingerprint | `fingerprints.py` |
| `0314275` | Tesla: FSD 14 FW test | `values.py`, `interface.py` |
| `01871c7` | Tesla: add new FSD 14 fingerprint | `fingerprints.py` |
| `c40213b` | Add Tesla FSD 14 firmware | `values.py` |
| `ec284cf` | Refactor: prioritize in-memory generated DBCs | DBC loading logic |

### panda

| Commit | Description | Files Changed |
|--------|-------------|---------------|
| `56920ec` | F4 panda support, Tesla/VW MEB ignition detection | `can_common.h`, `python/constants.py` |

---

## Files Modified for Tesla HW1 Support

### opendbc/car/tesla/

| File | Purpose | HW1-Specific Changes |
|------|---------|---------------------|
| `values.py` | Platform configs, safety flags, DBC mapping | `TESLA_MODEL_S_HW1`, `TESLA_MODEL_X_HW1` platform configs, `FLAG_HW1`, `LEGACY_CARS` tuple, Bosch radar DBC mapping |
| `interface.py` | Car interface, safety config setup | `_get_params_sx()` path, `teslaLegacy` safety model with `FLAG_HW1`, HW1 bus routing |
| `carstate.py` | CAN signal parsing | `update_legacy()` method, HW1 blinker fix (`STW_ACTN_RQ`), HW1 bus routing, `TeslaLegacyParams.NO_SDM1` |
| `carcontroller.py` | Steering/longitudinal control | `TeslaCANRaven` packer for HW1, HW1 skips `create_steering_allowed` (no APS_eacMonitor) |
| `radar_interface.py` | Radar data parsing | Bosch radar for HW1 (`BOSCH_RADAR_CARS`), 8Hz trigger fix, `last_radar_data` caching |
| `teslacan_legacy.py` | CAN message packing for legacy Tesla | `TeslaCANRaven` class, HW1-specific message packing |
| `fingerprints.py` | EPS firmware fingerprints | `TESLA_MODEL_S_HW1`, `TESLA_MODEL_X_HW1` FW versions |
| `tests/` | Unit tests | HW1-specific test files |

### opendbc/safety/modes/

| File | Purpose | HW1-Specific Changes |
|------|---------|---------------------|
| `tesla_legacy.h` | Legacy Tesla safety hooks | `tesla_hw1` flag, `TESLA_TX_LEGACY_HW1_MSGS`, `tesla_legacy_hw1_rx_checks`, 25Hz EPAS, HW1 message addresses (0x108 vs 0x106) |

### opendbc/dbc/

| File | Purpose | HW1-Specific Changes |
|------|---------|---------------------|
| `tesla_can.dbc` | Legacy CAN messages (HW1/HW2) | All messages for Model S/X HW1, `STW_ACTN_RQ` blinker signal, `GTW_carState`, `ESP_B`, `DI_torque1` |
| `tesla_radar_bosch_generated.dbc` | Bosch radar messages | Used by HW1/HW2 for radar data |
| `tesla_raven_party.dbc` | Model S HW3 party bus | Used by HW3, not HW1 |

### opendbc/car/

| File | Purpose | HW1-Specific Changes |
|------|---------|---------------------|
| `doc_definitions.py` | Car harness documentation | `tesla_model_s_hw1`, `tesla_model_x_hw1` harness definitions |
| `__init__.py` | Bus enum | Bus definitions used by HW1 routing |

### panda/

| File | Purpose | HW1-Specific Changes |
|------|---------|---------------------|
| `board/drivers/can_common.h` | CAN common driver code | Tesla legacy ignition detection (`GTW_status` 0x348), counter validation, Tesla legacy counter tracking |
| `python/constants.py` | Python device constants | Device type definitions |

---

## StarPilot-Specific Changes

These changes originate from StarPilot itself (not from xnor-tech) and must also be preserved during upstream merges.

### Tesla HW1 Fixes

| File | Change | Reason |
|------|--------|--------|
| `opendbc/car/tesla/carstate.py` | Model X HW1 blinker uses `STW_ACTN_RQ.TurnIndLvr_Stat` instead of `GTW_carState.BC_indicatorL/RStatus` | HW1 uses different blinker message on chassis bus |

### Documentation

| File | Purpose |
|------|---------|
| `opendbc/car/tesla/todo_HW1.md` | 38 tracked improvement items for HW1 |
| `opendbc/car/tesla/imports_to_maintain.md` | This file — import tracking |

---

## Comparison: StarPilot vs xnor-tech

| Component | Status | Notes |
|-----------|--------|-------|
| **opendbc/car/tesla/values.py** | **Identical** | No differences |
| **opendbc/car/tesla/interface.py** | **Minor** | Import ordering, indentation only |
| **opendbc/car/tesla/carstate.py** | **StarPilot ahead** | HW1 blinker fix (`STW_ACTN_RQ` for Model X HW1) |
| **opendbc/car/tesla/carcontroller.py** | **Identical** | No differences |
| **opendbc/car/tesla/radar_interface.py** | **Identical** | Includes 8Hz radar fix |
| **opendbc/car/tesla/teslacan_legacy.py** | **Identical** | No differences |
| **opendbc/car/tesla/fingerprints.py** | **Identical** | No differences |
| **opendbc/safety/modes/tesla_legacy.h** | **Identical** | No differences |
| **panda/board/drivers/can_common.h** | **Identical** | Includes Tesla legacy ignition + VW MEB |
| **panda/python/constants.py** | **Identical** | No differences |

---

## Diff Commands

Copy-paste ready commands to quickly check if upstream changed since last sync.

### Setup (run once)

```bash
# Add xnor-tech remotes
git remote add xnor-opendbc https://github.com/xnor-tech/opendbc.git
git remote add xnor-panda https://github.com/xnor-tech/panda.git

# Or update existing remotes
git remote set-url xnor-opendbc https://github.com/xnor-tech/opendbc.git
git remote set-url xnor-panda https://github.com/xnor-tech/panda.git

# Fetch latest
git fetch xnor-opendbc master-xnor --depth=1
git fetch xnor-panda master-xnor --depth=1
```

### opendbc — Tesla files

```bash
git diff xnor-opendbc/master-xnor:opendbc/car/tesla/ ./opendbc_repo/opendbc/car/tesla/
```

### opendbc — Safety modes

```bash
git diff xnor-opendbc/master-xnor:opendbc/safety/modes/tesla_legacy.h ./opendbc_repo/opendbc/safety/modes/tesla_legacy.h
```

### opendbc — DBC files

```bash
git diff xnor-opendbc/master-xnor:opendbc/dbc/tesla_can.dbc ./opendbc_repo/opendbc/dbc/tesla_can.dbc
git diff xnor-opendbc/master-xnor:opendbc/dbc/tesla_radar_bosch_generated.dbc ./opendbc_repo/opendbc/dbc/tesla_radar_bosch_generated.dbc
```

### opendbc — Panda firmware

```bash
git diff xnor-panda/master-xnor:board/drivers/can_common.h ./panda/board/drivers/can_common.h
git diff xnor-panda/master-xnor:python/constants.py ./panda/python/constants.py
```

### Full file list diff (quick check)

```bash
# Check if any Tesla-related files differ
for f in values.py interface.py carstate.py carcontroller.py radar_interface.py teslacan_legacy.py fingerprints.py; do
  diff <(git show xnor-opendbc/master-xnor:opendbc/car/tesla/$f) ./opendbc_repo/opendbc/car/tesla/$f >/dev/null 2>&1 \
    && echo "  OK: $f" || echo "DIFF: $f"
done
```

### Update "Last Synced" table

After reviewing diffs, update the commit hashes and dates in the [Last Synced](#last-synced) table:

```bash
git log -1 --format='%h %ci' xnor-opendbc/master-xnor
git log -1 --format='%h %ci' xnor-panda/master-xnor
```

---

## Merge Checklist

When merging upstream openpilot/opendbc/panda changes:

1. **Check for DBC changes** - `tesla_can.dbc`, `tesla_radar_bosch_generated.dbc`
2. **Check for safety mode changes** - `tesla_legacy.h`, `tesla.h`
3. **Check for car interface changes** - All files in `opendbc/car/tesla/`
4. **Check for panda ignition changes** - `can_common.h` ignition_can_hook
5. **Check for fingerprint updates** - `fingerprints.py` new FW versions
6. **Verify HW1 blinker path** - `STW_ACTN_RQ` for Model X HW1
7. **Verify radar caching** - `last_radar_data` for Bosch 8Hz
8. **Run Tesla HW1 safety tests** - `test_tesla_hw1.py`

---

## Known Differences from Upstream openpilot

These changes are NOT in the main commaai/openpilot repo and must be preserved:

- Tesla legacy support (Model S/X HW1/HW2/HW3)
- Tesla Raven party DBC
- Bosch radar support for legacy Tesla
- External panda support for HW2/HW3
- Tesla legacy safety mode (`tesla_legacy.h`)
- MG car support (also from xnor)

---

## Related

- [todo_HW1.md](./todo_HW1.md) — Full list of 38 HW1 improvement items
- [tesla_legacy.h](../../safety/modes/tesla_legacy.h) — Safety layer source
- [carstate.py](./carstate.py) — CAN parsing source
