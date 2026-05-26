# Debug Session Notes - Tesla AP1 (HW1) on staging2-tici

## Session Context

- **Date:** 2026-05-16
- **Branch:** `staging2-tici`
- **Commit:** `146225c56` ("restore embedded panda from upstream (supports C3 type 0x06)")
- **Parent:** `c4836b5d2` ("upstream staging-tici + fork submodules (panda, opendbc)")
- **Origin:** `git@github.com:P6g9YHK6/SunnyPilot-TeslaHW1.git`
- **Upstream:** `https://github.com/sunnyhaibin/sunnypilot.git`

## Device

- **Type:** Comma three (tici)
- **IP:** 100.94.205.83
- **SSH:** `comma@100.94.205.83`
- **Path:** `/data/openpilot` → staging2-tici branch (cloned from the fork)

## Hardware Setup

- **Panda:** Panda DOS (connected via USB to C3)
  - Firmware: `DOS_v2_legacy_0x06` (build Jul 26 2024)
  - Voltage: 5.026V, Current: 174mA (normal)
  - No `/dev/panda*` USB entries visible (expected for SPI-connected on C3; this may be the internal panda)
- **Car:** Tesla Model S 2014-2016 (AP1 / HW1)
  - Fingerprint: `TESLA_MODEL_S_HW1` (confirmed matching in logs)

## Key Observations

| Parameter | Expected | Observed | Notes |
|-----------|----------|----------|-------|
| `ignitionLine` | true when car on | `false` | Tesla has no 12V ignition signal on OBD-II |
| `ignitionCan` | true when car on | `false` | **ROOT CAUSE** - car possibly not started during testing |
| `deviceState.started` | true when ignition | `false` | Consequence of no ignition |
| `pcmCruise` | true (default) | `true` | OK |
| `openpilotLongitudinalControl` | true | `true` | OK |
| `safetyModel` | `teslaLegacy` | `teslaLegacy` | OK |
| `safetyParam` | 9 (HW1=8\|LONG_CONTROL=1) | **146** | **ANOMALY** |
| `alternativeExperience` | varies | 1 | MADS not enabled (ENABLE_MADS=1024) |
| MADS | off | off | `alternativeExperience=1` |

## The `safetyParam=146` Anomaly

### Expected value for HW1

From `opendbc_repo/opendbc/car/tesla/interface.py:67-70`:
```python
if candidate in (CAR.TESLA_MODEL_S_HW1, CAR.TESLA_MODEL_X_HW1):
  ret.safetyConfigs = [
    get_safety_config(structs.CarParams.SafetyModel.teslaLegacy,
                      int(TeslaSafetyFlags.FLAG_HW1)),  # = 8
  ]
```

Then line 91:
```python
ret.safetyConfigs[0].safetyParam |= TeslaSafetyFlags.LONG_CONTROL.value  # |= 1
```

**Expected final safetyParam: 9** (binary: `00001001` = HW1 | LONG_CONTROL)

### Observed value: 146 (binary: `10010010`)

| Bit | Value | Flag | Expected for HW1? |
|-----|-------|------|-------------------|
| 0 | 0 | - | Should be 1 (LONG_CONTROL) |
| 1 | 2 | FSD_14 | **NO** - HW1 doesn't use FSD_14 |
| 2 | 4 | FLAG_EXTERNAL_PANDA | **NO** - HW1 doesn't support external panda |
| 3 | 8 | FLAG_HW1 | Not set |
| 4 | 16 | FLAG_HW2 | **NO** - car is HW1, not HW2 |
| 5 | 32 | FLAG_HW3 | No |
| 6 | 64 | _(undefined)_ | No |
| 7 | 128 | _(undefined)_ | **UNKNOWN** - not defined in TeslaSafetyFlags |

This suggests either:
1. The `CarParams` cached in params is stale from a previous branch/interim state
2. The car fingerprinted as something other than HW1 at some point
3. Something in sunnypilot or a custom override modified the safety param

### Key question: Is safetyParam=146 from a CURRENT run or a STALE cached value?

The user read CarParams from Params db. If the system ran previously with different code (e.g., staging-tici before the submodule updates), the cached CarParams might have the wrong value. The fix: **delete params cache** and reboot to force fresh fingerprinting.

## Ignition Detection for Tesla Legacy

Tesla vehicles do NOT have a standard 12V ignition signal on OBD-II pin 1. Instead, the **panda firmware** uses CAN-based ignition detection:

1. The panda's `ignition_can_hook` (in `can_common.h` from xnor-tech/panda) monitors CAN bus for message `0x348` (`GTW_status`)
2. Bit 0 of data byte 0 (`GTW_driveRailReq`) being set indicates the car is in drive/ready state
3. When detected, the panda sets `ignitionCan = true` in its health packet
4. openpilot's manager checks `any(ps.ignitionLine or ps.ignitionCan for ps in pandaStates)` to decide whether to start onroad processes

**The panda firmware source is NOT in this repo** (only prebuilt .bin files in `panda/board/obj/`).
The panda firmware comes from [xnor-tech/panda](https://github.com/xnor-tech/panda).

### Potential ignition detection failure modes:

1. **Panda firmware lacks Tesla CAN ignition detection** - The flashed firmware `DOS_v2_legacy_0x06` may not include the `ignition_can_hook` for `GTW_status`. Verify by examining the Panda DOS firmware source.

2. **CAN bus routing issue** - The Panda DOS might not be on the CAN bus where `GTW_status` (0x348) is transmitted. For Tesla HW1, the chassis CAN bus is bus 0.

3. **Internal + external panda confusion** - C3 has an SPI-connected internal panda AND the USB-connected Panda DOS. If both are active:
   - `pandaStates[0]` = internal C3 panda (not connected to car CAN)
   - `pandaStates[1]` = Panda DOS (connected to car CAN)
   - Manager checks ALL pandas - if the internal one has no ignition, it might override
   - Actually, manager uses `any()` so either being true should work

4. **Car not actually in "on" state** - The user may not have shifted to Drive during testing. `GTW_status` only appears when the car is powered on.

## Key File Locations

| File | Purpose |
|------|---------|
| `opendbc_repo/opendbc/car/tesla/interface.py` | Car interface, sets safetyConfigs |
| `opendbc_repo/opendbc/car/tesla/values.py` | TeslaSafetyFlags, platform configs |
| `opendbc_repo/opendbc/safety/modes/tesla_legacy.h` | C safety code running on panda |
| `opendbc_repo/opendbc/car/tesla/teslacan_legacy.py` | CAN message packing for legacy |
| `opendbc_repo/opendbc/car/tesla/carcontroller.py` | Car controller (uses TeslaCANRaven for legacy) |
| `opendbc_repo/opendbc/car/tesla/carstate.py` | CAN state parsing |
| `opendbc_repo/opendbc/sunnypilot/car/tesla/values.py` | SP flags (HAS_VEHICLE_BUS=1, COOP_STEERING=2) |
| `selfdrive/pandad/pandad.py` | Panda discovery, sorting, flashing |
| `selfdrive/selfdrived/selfdrived.py` | Safety config validation |
| `panda/python/__init__.py` | Python panda library, health packet parsing |
| `panda/board/obj/` | Prebuilt panda firmware binaries |
| `opendbc_repo/opendbc/dbc/tesla_can.dbc` | CAN DBC - GTW_status at ID 0x348 (line 439) |
| `opendbc_repo/opendbc/car/tesla/todo_HW1.md` | HW1 limitations (609 lines) |

## Critical HW1 Limitations (from todo_HW1.md)

1. **No FLAG_EXTERNAL_PANDA support** - HW1 only has 1 safety config; external Panda DOS not officially supported
2. **No FSD_14 flag** - HW1 doesn't use FSD_14 safety features
3. **All checksums ignored** - `ignore_checksum=true, ignore_counter=true` for all messages
4. **EPS at 25 Hz** (vs 100 Hz on HW3)
5. **Chassis bus is 0** (HW3 uses bus 1)
6. **Only 2 TX messages**: `DAS_steeringControl` (0x488) and `DAS_control` (0x2b9)

## Safety Config Architecture for External Panda

The system uses positional assignment:
- `pandaStates[0]` (internal panda, sorted first) gets `safetyConfigs[0]`
- `pandaStates[1]` (external panda, sorted second) gets `safetyConfigs[1]` (if it exists)
- For HW1: only `safetyConfigs[0]` exists, so `pandaStates[1]` would fall to the `else` branch and check `IGNORED_SAFETY_MODES`

In `selfdrived.py:311-316`:
```python
for i, pandaState in enumerate(self.sm['pandaStates']):
  if i < len(self.CP.safetyConfigs):
    safety_mismatch = pandaState.safetyModel != ...
  else:
    safety_mismatch = pandaState.safetyModel not in IGNORED_SAFETY_MODES
  if safety_mismatch:
    self.events.add(EventName.controlsMismatch)
```

If the internal C3 panda doesn't have `teslaLegacy` safety model, or the Panda DOS doesn't match, there could be a `controlsMismatch` that prevents engagement.

## Scripts to Run On-Device for Next Session

### 1. Verify safetyParam source and check CarParams

```bash
ssh comma@100.94.205.83

# Check current fresh CarParams (delete cached, force re-fingerprint, then reboot)
# WARNING: This will reset ALL params:
rm -f /data/params/d/CarParams*
# Then use params library
python3 -c "
import os, sys
sys.path.insert(0, '/data/openpilot')
os.environ['PYTHONPATH'] = '/data/openpilot'
from openpilot.common.params import Params
p = Params()
cp = p.get('CarParams')
if cp:
    from opendbc.car.structs import CarParams
    car_params = CarParams.from_bytes(cp)
    print('carName:', car_params.carName)
    print('PCM cruise:', car_params.pcmCruise)
    print('openpilotLong:', car_params.openpilotLongitudinalControl)
    for i, sc in enumerate(car_params.safetyConfigs):
        print(f'  safetyConfigs[{i}]: model={sc.safetyModel}, param={sc.safetyParam}')
    print('altExp:', car_params.alternativeExperience)
else:
    print('No CarParams cached yet')
"
```

### 2. Monitor ignition state while car is on

```bash
ssh comma@100.94.205.83

# First, ensure PYTHONPATH is set
export PYTHONPATH=/data/openpilot

# Run the ignition/car state monitor with proper imports
python3 -c "
import cereal.messaging as messaging
import time

sm = messaging.SubMaster(['pandaStates', 'deviceState', 'carState', 'carParams'])

print('Waiting for messages... (go start the car!)')
print('')
start = time.time()
while time.time() - start < 120:  # 2 minute window
    sm.update(1000)
    
    ign_line = False
    ign_can = False
    ptypes = []
    for ps in sm['pandaStates']:
        ign_line = ign_line or ps.ignitionLine
        ign_can = ign_can or ps.ignitionCan
        ptypes.append(str(ps.pandaType))
    
    started = sm['deviceState'].started if sm.recv_frame['deviceState'] > 0 else '?'
    
    status = ''
    if sm.updated['carState'] and sm.recv_frame['carState'] > 0:
        status = f'gear={sm[\"carState\"].gearShifter} enabled={sm[\"carState\"].cruiseState.enabled}'
    
    elapsed = int(time.time() - start)
    print(f'[{elapsed}s] ignLine={ign_line} ignCan={ign_can} started={started} pandas={ptypes} {status}', end='\r')
    
    if started == True:
        print(f\"\\nIGNITION DETECTED at {elapsed}s!\")
        break
print('')
"
```

### 3. Check how many pandas are detected

```bash
ssh comma@100.94.205.83
export PYTHONPATH=/data/openpilot
python3 -c "
import os
os.environ['PYTHONPATH'] = '/data/openpilot'
import panda.python as panda
print('All pandas:', panda.Panda.list())
for s in panda.Panda.list():
    p = panda.Panda(s)
    h = p.health()
    print(f'  Panda {s}:')
    print(f'    type={p.get_type()} internal={p.is_internal()} hw_type={p.get_mcu_type()}')
    print(f'    ignitionLine={h[\"ignition_line\"]} ignitionCan={h[\"ignition_can\"]}')
    print(f'    voltage={h[\"voltage\"]}mA current={h[\"current\"]}mA')
    print(f'    safety_model={h[\"safety_model\"]} safety_param={h[\"safety_param\"]}')
    p.close()
"
```

### 4. Check current running safety config on panda

```bash
ssh comma@100.94.205.83
export PYTHONPATH=/data/openpilot
python3 -c "
import cereal.messaging as messaging
import time

sm = messaging.SubMaster(['pandaStates'])
time.sleep(2)
sm.update(0)

for i, ps in enumerate(sm['pandaStates']):
    print(f'pandaStates[{i}]:')
    print(f'  pandaType={ps.pandaType}')
    print(f'  safetyModel={ps.safetyModel}')
    print(f'  safetyParam={ps.safetyParam}')
    print(f'  ignitionLine={ps.ignitionLine}')
    print(f'  ignitionCan={ps.ignitionCan}')
    print(f'  faults={ps.faults}')
"
```

### 5. Dump raw CAN traffic to verify GTW_status is on bus

```bash
ssh comma@100.94.205.83
export PYTHONPATH=/data/openpilot
python3 -c "
import cereal.messaging as messaging
import time

sm = messaging.SubMaster(['can'])
print('Monitoring CAN for GTW_status (0x348)...')
start = time.time()
while time.time() - start < 30:
    sm.update(500)
    if sm.updated['can'] and sm.recv_frame['can'] > 0:
        for msg in sm['can']:
            if msg.address == 0x348:
                databytes = bytes(msg.dat).hex()
                bus = msg.bus
                print(f'Got GTW_status on bus {bus}: {databytes}')
"
```

### 6. Verify opendbc_repo submodule is at correct commit

```bash
cd /home/samy/Projects/SunnyPilot-TeslaHW1
git submodule status
# Expected: 7e3ba8aab86b7dbcc2bd2f1944ac240bc5934c6f opendbc_repo (heads/master)
```

## Troubleshooting Workflow (Next Session)

### Step 1: Connect and verify device state
```bash
ssh comma@100.94.205.83
```

### Step 2: Delete stale params and reboot
```bash
# Remove cached CarParams to force fresh fingerprinting
python3 -c "
import os
os.environ['PYTHONPATH']='/data/openpilot'
from openpilot.common.params import Params
# Delete CarParams to force re-fingerprint
Params().remove('CarParams')
print('CarParams deleted from params cache')
"
# Reboot
sudo reboot
```

### Step 3: After reboot, run the ignition monitor (Script 2 above)

### Step 4: If still no ignition:
- Run Script 3 to check panda count and health
- Run Script 4 to check safety configs running on pandas
- Run Script 5 to dump CAN and check for GTW_status (requires car ON)

### Step 5: If GTW_status NOT seen on CAN:
- Check CAN bus connection/termination
- Try tapping into a different CAN bus on the Tesla OBD-II

### Step 6: If GTW_status IS seen but ignitionCan=False:
- The Panda DOS firmware may lack Tesla CAN ignition detection
- Need to flash or patch panda firmware with `ignition_can_hook` for GTW_status
- Check xnor-tech/panda source for `can_common.h` `ignition_can_hook` implementation

### Step 7: If safetyParam=146 persists after fresh CarParams:
- Check if multiple pandas are detected (Script 3)
- Check if the wrong safety config is being applied (Script 4)
- May need to add FLAG_EXTERNAL_PANDA support for HW1 (modify interface.py)

## Notes for stagin2-tici Branch

This branch has 2 commits ahead of staging-tici:
1. `146225c56` - restore embedded panda from upstream (supports C3 type 0x06)
2. `c4836b5d2` - upstream staging-tici + fork submodules (panda, opendbc)

The opendbc_repo submodule was updated from `12fb47c0b` → `7e3ba8aab` (heads/master).
Key opendbc_repo changes: DBC merge additions (APS_eacMonitor, RCM_status, standstill resume fix, HW1 car list).
The Tesla interface.py file did NOT change between the submodule versions.
