# Tesla HW1 (Model S/X 2014-16) - Improvement TODO List

## Overview

Tesla HW1 (Model S/X 2014-16) is the least capable Tesla variant for openpilot integration. This document tracks all known missing features, signals, and improvements needed to bring HW1 to parity with better-supported platforms.

**Current Status:** Legacy safety model (`teslaLegacy`), 25 Hz EPS, no checksum/counter validation, single-panda only, no external panda support.

---

## Critical Missing Signals

### 1. APS_eacMonitor (0x27d) - Steering Permission
- **Priority:** HIGH
- **Files:** `carcontroller.py:58`, `tesla_legacy.h:218-226`
- **Issue:** HW1 does not send `APS_eacMonitor` message. HW2/HW3 use this to validate steering permission. HW1 is excluded from `steering_allowed` messages entirely.
- **TODO:**
  - [ ] Investigate if APS_eacMonitor exists on HW1 at a different address or on a different bus
  - [ ] If unavailable, document the fallback steering permission mechanism
  - [ ] Add HW1-specific steering permission validation in safety layer
  - [ ] Update `carcontroller.py` to handle HW1 steering enable path
- **Unity Reference:** Unity has `EPB_epasControl` (0x214, ID 532) with `EPB_epasEACAllow` signal that may serve as the HW1 equivalent for steering permission. Also has `DAS_pscControl` (0x219, ID 537) with `DAS_eacState` signal. Both are defined in Unity's `tesla_can.dbc`.

### 2. ESP_private1 (0x155) - Brake System Data
- **Priority:** MEDIUM
- **Files:** `tesla_legacy.h:259-265`
- **Issue:** HW3 receives `ESP_private1` on bus 1. HW1 chassis bus (0) does not expose this message.
- **TODO:**
  - [ ] Search HW1 DBC (`tesla_can.dbc`) for equivalent brake system signals
  - [ ] Map ESP_private1 signals to HW1 equivalents if they exist
  - [ ] Update `carstate.py` to parse HW1 brake data
- **Unity Reference:** Unity's DBC has `ESP_145h` (0x145, ID 325) which is the HW1 equivalent of ESP private data. Contains: `ESP_brakeMasterCylPress` (brake master cylinder pressure in bar), `ESP_longitudinalAccel`, `ESP_lateralAccel`, `ESP_vehicleStandstillSts` (standstill detection), `ESP_wheelSpeedsQF` (wheel speed quality flags), `ESP_espModeActive`, `ESP_btcTargetState`, `ESP_ptcTargetState`. Also has `ESP_ACC` (0x125, ID 293) with `Long_Acceleration` and `Lat_Acceleration` from ESP's internal accelerometers.

### 3. BrakeMessage (0x20a) - Brake Status
- **Priority:** MEDIUM
- **Files:** `tesla_legacy.h:259-265`
- **Issue:** HW3 receives `BrakeMessage` on bus 1. Not available on HW1.
- **TODO:**
  - [ ] Find HW1 brake status message location
  - [ ] Map brake pressure, brake applied, and brake hold signals
  - [ ] Add to `carstate.py` parsing
- **Unity Reference:** Both DBCs define `BrakeMessage` (0x20a, ID 522) with `driverBrakeStatus` signal. This exists in both Unity and xnor DBCs at the same address. Additionally, Unity has `ESP_145h` (ID 325) with `ESP_brakeMasterCylPress` (bar) and `ESP_brakeMasterCylPressQF` for brake pressure quality. For iBooster-equipped HW1, Unity also has `ECU_BrakeStatus` (0x554, ID 1364) with `BrakeApplied`, `BrakePedalPosition`, `DriverBrakeApplied`, `BrakeOK` signals.

### 4. DI_state (0x368) - Drive Inverter State
- **Priority:** MEDIUM
- **Files:** `tesla_legacy.h:259-265`
- **Issue:** HW3 receives `DI_state` on bus 1. Not available on HW1.
- **TODO:**
  - [ ] Find HW1 drive inverter state signals
  - [ ] Map gear selection, inverter status, and motor torque signals
  - [ ] Add to `carstate.py` parsing
- **Unity Reference:** Unity's DI_state (ID 872, 0x368) includes: `DI_cruiseState`, `DI_cruiseSet` (set speed), `DI_digitalSpeed` (display speed), `DI_analogSpeed`, `DI_aebState`, `DI_systemState`, `DI_vehicleHoldState`, `DI_proximity`, `DI_driveReady`, `DI_regenLight`, `DI_state`, `DI_immobilizerState`, `DI_speedUnits`. **CRITICAL BIT LAYOUT DIFFERENCE:** Unity places `DI_digitalSpeed` at bit 32 and `DI_cruiseSet` at bit 48 (8 bits, scale 1). xnor reverses these: `DI_cruiseSet` at bit 32 (9 bits, scale 0.5) and `DI_digitalSpeed` at bit 48 (8 bits, scale 1). Verify which layout is correct for your car before using either.

### 5. DI_state Bit Layout Conflict (CRITICAL)
- **Priority:** CRITICAL
- **Files:** `tesla_can.dbc`, `carstate.py`, `tesla_legacy.h`
- **Issue:** Unity and xnor DBCs define `DI_cruiseSet` and `DI_digitalSpeed` at swapped bit positions with different sizes/scales:
  - **Unity:** `DI_digitalSpeed` bit 32 (8 bits, scale 1) | `DI_cruiseSet` bit 48 (8 bits, scale 1)
  - **xnor:** `DI_cruiseSet` bit 32 (9 bits, scale 0.5) | `DI_digitalSpeed` bit 48 (8 bits, scale 1)
- Using the wrong layout silently corrupts cruise set speed and display speed values with no obvious error.
- **TODO:**
  - [ ] Log raw CAN bytes for DI_state (0x368, ID 872) on HW1 hardware and decode both layouts
  - [ ] Determine which bit layout matches actual vehicle behavior (compare set speed vs dash display)
  - [ ] Update DBC and carstate.py parsing to use the verified layout
  - [ ] Document which HW1 model years/variants use which layout (if mixed)

### 6. DAS_status / DAS_status2 Restructuring (HIGH)
- **Priority:** HIGH
- **Files:** `tesla_can.dbc`, `carstate.py`
- **Issue:** Unity and xnor have different signal layouts in DAS_status (0x399, ID 921) and DAS_status2 (0x389, ID 905):
  - Unity's `DAS_status` has `DAS_lssState` at bit 29 (3 bits) — removed in xnor, shifting `DAS_sideCollisionAvoid` from bit 32→30, `DAS_sideCollisionWarning` from 34→32, `DAS_sideCollisionInhibit` from 36→34
  - xnor adds `DAS_csaState` at bit 35 in this message (Unity has it in DAS_status2)
  - Unity's `DAS_status2` has `DAS_relaxCruiseLimits` at bit 31 and `DAS_csaState` at bit 32 — both removed in xnor which places `DAS_lssState` at bit 31 instead
- Using the wrong layout causes side collision warnings, CSA state, and LSS state to be misinterpreted.
- **TODO:**
  - [ ] Log raw CAN bytes for DAS_status (0x399, ID 921) and DAS_status2 (0x389, ID 905) on HW1
  - [ ] Decode both layouts and verify against vehicle behavior
  - [ ] Update DBC to match verified layout
  - [ ] Update carstate.py parsing accordingly

### 7. VCRIGHT_silla2 (0x39f) - Right Seat Data
- **Priority:** LOW
- **Files:** `tesla_legacy.h`
- **Issue:** HW3 receives right seat data. Not available on HW1.
- **TODO:**
  - [ ] Determine if this signal is needed for safety features
  - [ ] If needed, find HW1 equivalent

---

## Performance Improvements

### 8. EPS Update Rate - 25 Hz to Higher
- **Priority:** HIGH
- **Files:** `carstate.py:185-188`, `tesla_legacy.h:241-249`
- **Issue:** HW1 EPAS runs at 25 Hz vs 100 Hz on HW3. This limits lateral control responsiveness.
- **TODO:**
  - [ ] Investigate if HW1 EPS can be polled at higher rate
  - [ ] If not, tune lateral controller for 25 Hz constraints
  - [ ] Add EPS rate warning in UI if below threshold
  - [ ] Consider interpolation/extrapolation for smoother control

### 9. CAN Message Address Differences
- **Priority:** MEDIUM
- **Files:** `carstate.py`, `tesla_legacy.h`, `tesla_can.dbc`
- **Issue:** DI_torque1 is at 0x108 on HW1 vs 0x106 on HW2/HW3. Requires separate parsing paths.
- **TODO:**
  - [ ] Audit all CAN message address differences between HW1 and HW2/HW3
  - [ ] Create a comprehensive address mapping table
  - [ ] Consolidate parsing logic where possible
  - [ ] Document all HW1-specific message addresses

---

## Safety Layer Improvements

### 10. Checksum and Counter Validation
- **Priority:** HIGH
- **Files:** `tesla_legacy.h:241-249`
- **Issue:** All HW1 messages have `ignore_checksum=true, ignore_counter=true`. No message integrity validation.
- **TODO:**
  - [ ] Investigate if HW1 messages have checksums at different bit positions
  - [ ] If checksums exist, implement validation in safety layer
  - [ ] If no checksums, document the risk and add runtime signal plausibility checks
  - [ ] Add counter validation where possible
  - [ ] Implement signal range checks as fallback validation

### 11. External Panda Support
- **Priority:** HIGH
- **Files:** `values.py:43-118`, `tesla_legacy.h:277-279`
- **Issue:** HW1 does not support external panda for longitudinal control. Single-panda architecture only.
- **TODO:**
  - [ ] Investigate if external panda can be added to HW1 architecture
  - [ ] If possible, implement external panda TX path for HW1
  - [ ] Update safety flags to allow `FLAG_EXTERNAL_PANDA` for HW1
  - [ ] Document hardware modifications required

### 12. TX Message Expansion
- **Priority:** MEDIUM
- **Files:** `tesla_legacy.h:228-231`
- **Issue:** HW1 only transmits `DAS_steeringControl` (0x488) and `DAS_control` (0x2b9). Missing `APS_eacMonitor` and other permission messages.
- **TODO:**
  - [ ] Identify all TX messages needed for full feature parity
  - [ ] Add missing TX messages to HW1 safety config
  - [ ] Test each TX message on HW1 hardware
- **Unity Reference:** Unity transmits significantly more messages for full IC integration. For HUD/cluster display: `DAS_object` (0x309, ID 777), `DAS_lanes` (0x239, ID 569), `DAS_telemetry` (0x3A9, ID 937), `DAS_bodyControls` (0x3E9, ID 1001), `DAS_warningMatrix` messages. For gas/brake control: `GAS_COMMAND` (0x551, ID 1361), `GAS_SENSOR` (ID 1362), `ECU_BrakeCommand` (0x553, ID 1363), `ECU_BrakeStatus` (ID 1364). For AP status: `DAS_status` (0x399, ID 921), `DAS_status2` (0x389, ID 905). Many of these are defined in Unity's DBC and would need corresponding definitions in the safety layer and DBC before transmission.

---

## UI and Driver Feedback

### 13. Gap Adjust Button
- **Priority:** HIGH
- **Files:** `carstate.py:158`, `carstate.py:249`
- **Issue:** No gap adjust button detection. TODO noted in code.
- **TODO:**
  - [ ] Find gap adjust button signal in HW1 DBC
  - [ ] Add button event parsing in `carstate.py`
  - [ ] Map to `buttonEvents` in car state
  - [ ] Test button functionality on HW1 hardware

### 14. HUD Control
- **Priority:** HIGH
- **Files:** `carcontroller.py:76`
- **Issue:** HUD control not implemented. TODO noted in code.
- **TODO:**
  - [ ] Find HUD/cluster display messages in HW1 DBC
  - [ ] Implement HUD message packing in `teslacan_legacy.py`
  - [ ] Add lane lines, lead car, and speed display to HUD
  - [ ] Test on HW1 hardware
- **Unity Reference:** Unity has a complete reference implementation: `HUD_module.py` handles all IC integration. Key messages it transmits at 10Hz on CAN bus 0: `DAS_object` (0x309, ID 777) for lead vehicle display (2-object tracking with type, Dx, Dy, VxRel); `DAS_lanes` (0x239, ID 569) for lane geometry (polynomial C0-C3, lane existence, usage); `DAS_telemetry` (0x3A9, ID 937) for lane line types/colors/qualities/crossing state. At 2Hz: `DAS_status` (0x399, ID 921) for AP state, blind spot, speed limit, hands-on, ALCA; `DAS_status2` (0x389, ID 905) for ACC speed limit, CSA state, FCW. At 1Hz: `DAS_warningMatrix0/1/3` for warning indicators. Also sends synthetic `DAS_bodyControls` for turn signals/hazards. All these messages are defined in Unity's `tesla_can.dbc`.

### 15. Lane Departure Warning (LDW)
- **Priority:** MEDIUM
- **Files:** `carstate.py`, `carcontroller.py`
- **Issue:** No LDW signal detection or display.
- **TODO:**
  - [ ] Find LDW signals in HW1 DBC
  - [ ] Add LDW state parsing
  - [ ] Implement LDW alert display in UI
- **Unity Reference:** Unity's `DAS_status` (0x399, ID 921) has `DAS_laneDepartureWarning` signal (3 bits at bit 37, scale 1). Unity's `DAS_telemetry` (0x3A9, ID 937) includes `DAS_telLeftLaneCrossing` and `DAS_telRightLaneCrossing` (1 bit each) for real-time lane departure detection. Unity transmits `DAS_lanes` (ID 569) with lane geometry and `DAS_telemetry` with lane type/color/quality — both are useful for HUD display and LDW logic.

### 16. Forward Collision Warning (FCW)
- **Priority:** MEDIUM
- **Files:** `carstate.py`, `carcontroller.py`
- **Issue:** No FCW signal detection or display.
- **TODO:**
  - [ ] Find FCW signals in HW1 DBC
  - [ ] Add FCW state parsing
  - [ ] Implement FCW alert in UI
- **Unity Reference:** Unity's `DAS_status` (0x399, ID 921) has `DAS_forwardCollisionWarning` (2 bits at bit 22). Unity's `DAS_status2` (0x389, ID 905) has `DAS_longCollisionWarning` (4 bits at bit 48) with detailed FCW reason codes (CIPV, MCVL, MCVR, cut-in, pedestrian, stop sign, traffic light, IPSO). Both signals are defined in Unity's `tesla_can.dbc`.

### 17. Lead Distance Display
- **Priority:** MEDIUM
- **Files:** `carstate.py`, `carcontroller.py`
- **Issue:** No following distance bars displayed to driver.
- **TODO:**
  - [ ] Find lead distance signals in HW1 DBC
  - [ ] Map to UI display
  - [ ] Test on HW1 hardware
- **Unity Reference:** Unity transmits `DAS_object` (0x309, ID 777) at 10Hz on CAN bus 0 with 2-object lead vehicle tracking. Contains: `DAS_leadVehDx` (distance, 8 bits, scale 0.5, 0-127m), `DAS_leadVehVxRel` (relative speed, 4 bits, scale 4, -30 to 26 m/s), `DAS_leadVehDy` (lateral offset, 7 bits, scale 0.35), `DAS_leadVehType` (3-bit classification: 0=invalid, 1=model3, 2=model3_radar, 3=tesla, 4=car, 5=truck, 6=motorcycle, 7=bicycle), `DAS_leadVehRelevantForControl`. Second lead vehicle has same signals at offset. This message emulates what the factory DAS would normally send to the IC for lead vehicle display.

### 18. Invalid LKAS Setting Detection
- **Priority:** MEDIUM
- **Files:** `carstate.py:141`
- **Issue:** `invalidLkasSetting` detection not implemented for HW1/Model X. TODO: find signal for TESLA_MODEL_X and HW2.5 vehicles.
- **TODO:**
  - [ ] Find DAS_settings equivalent on HW1
  - [ ] Implement `invalidLkasSetting` detection
  - [ ] Add to `carstate.py` parsing

---

## Longitudinal Control

### 19. Native Stop-and-Go Support
- **Priority:** HIGH
- **Files:** `carstate.py`, `carcontroller.py`
- **Issue:** Tesla uses workaround (standstill check) instead of native SNG. No `autoResumeSng` flag.
- **TODO:**
  - [ ] Investigate if HW1 supports native SNG
  - [ ] If yes, implement `autoResumeSng` flag
  - [ ] If no, improve current workaround for smoother operation
  - [ ] Test SNG behavior on HW1 hardware
- **Unity Reference:** Unity has `ESP_145h` (ID 325) with `ESP_vehicleStandstillSts` (2 bits at bit 30) for explicit standstill detection from ESP. Unity also reads `DI_vehicleHoldState` from `DI_state` (ID 872) for hold state. Unity's `HUD_module` sends `DAS_accState` = 3 (ACC_HOLD) in `DAS_control` (0x2B9) during standstill, which may be the proper factory way to signal hold mode. Unity also sends `DAS_status` signals `DAS_autoParked`, `DAS_autoparkWaitingForBrake`, etc. for state management.

### 20. Longitudinal PID Tuning
- **Priority:** MEDIUM
- **Files:** `interface.py`, `carcontroller.py`
- **Issue:** Tesla uses direct accel control without per-platform PID gains.
- **TODO:**
  - [ ] Characterize HW1 longitudinal response
  - [ ] Implement per-platform PID tuning for HW1
  - [ ] Tune for smooth acceleration and deceleration
  - [ ] Test across speed range
- **Unity Reference:** Unity's `PCC_module.py` implements a PID-based speed controller for the pedal interceptor path (PRE-AP cars). It uses hysteresis-based speed control with configurable pedal calibration (`PEDAL_BP`/`PEDAL_V` lookup tables, `tunes.py`). Unity also supports three distinct longitudinal paths (pedal interceptor, DAS_control for AP1, DAS_longControl for AP2) with different tuning per path. The `jerkMin`/`jerkMax` signals in `DAS_control` (0x2B9) are used for jerk limiting. xnor's approach uses jerk ramping (progressive jerk limits during gas override) which is complementary.

### 21. Longitudinal Actuator Delay
- **Priority:** MEDIUM
- **Files:** `interface.py`
- **Issue:** No actuator delay tuning for HW1.
- **TODO:**
  - [ ] Measure HW1 longitudinal actuator delay
  - [ ] Add `longitudinalActuatorDelay` to HW1 params
  - [ ] Tune for optimal response

### 22. Radar Integration
- **Priority:** LOW
- **Files:** `radar_interface.py`
- **Issue:** HW1 uses Bosch radar (older generation). No radar disable option.
- **TODO:**
  - [ ] Characterize Bosch radar performance on HW1
  - [ ] Implement radar disable flag if needed
  - [ ] Fuse radar and camera data optimally
  - [ ] Test in various conditions
- **Unity Reference:** Unity's `radar_interface.py` supports configurable radar offset via `TinklaRadarOffset`, upside-down mounting, and behind-nosecone mounting for PRE-AP retrofits. It has an `SGUErrorIgnore` option. Unity also reads `UI_radarMapData` (ID 696) and `UI_radarTargetDx`/`UI_radarTargetTrustMap` for radar map data from the IC. Unity's `DAS_object` (ID 777) re-transmits fused radar data as factory DAS messages — useful for IC display and potentially for other ECUs that expect DAS_object.

---

## Lateral Control

### 23. Per-Platform Lateral Tuning
- **Priority:** MEDIUM
- **Files:** `interface.py`, `values.py`
- **Issue:** All Teslas use same lateral limits. No per-platform torque tuning.
- **TODO:**
  - [ ] Characterize HW1 steering response
  - [ ] Implement HW1-specific lateral tuning
  - [ ] Tune steering rate and max torque for HW1
  - [ ] Test on winding roads

### 24. Wheel Speed Factor
- **Priority:** LOW
- **Files:** `interface.py`
- **Issue:** Wheel speed factor not set for Tesla.
- **TODO:**
  - [ ] Measure HW1 wheel speed accuracy
  - [ ] Calculate wheel speed factor
  - [ ] Add to HW1 params

### 25. Steer Ratio
- **Priority:** LOW
- **Files:** `interface.py`
- **Issue:** Steer ratio uses fixed estimate, not measured per-car.
- **TODO:**
  - [ ] Measure HW1 steering ratio
  - [ ] Add accurate steer ratio to HW1 params
  - [ ] Test lateral controller with corrected ratio

### 26. Lateral Jerk Limits
- **Priority:** LOW
- **Files:** `interface.py`
- **Issue:** Fixed lateral jerk limits, not per-platform.
- **TODO:**
  - [ ] Characterize HW1 lateral jerk limits
  - [ ] Implement HW1-specific jerk limits
  - [ ] Test for comfort and safety

---

## Vehicle State Detection

### 27. Transmission Type Detection
- **Priority:** LOW
- **Files:** `interface.py`, `carstate.py`
- **Issue:** Transmission type not detected for Tesla.
- **TODO:**
  - [ ] Determine if transmission type is relevant for Tesla (single-speed)
  - [ ] If not relevant, document why
  - [ ] If relevant, add detection logic

### 28. Hybrid/EV Detection
- **Priority:** LOW
- **Files:** `interface.py`
- **Issue:** No hybrid/EV flag for Tesla (all Teslas are EV).
- **TODO:**
  - [ ] Add `EV` flag to Tesla safety model
  - [ ] Implement EV-specific behaviors if needed (regen braking handling)

### 29. Blind Spot Detection Enhancement
- **Priority:** MEDIUM
- **Files:** `carstate.py`, `values.py`
- **Issue:** Tesla only has basic `DAS_blindSpotRearLeft/Right` detection. No BSM mirror control.
- **TODO:**
  - [ ] Find BSM mirror control messages in HW1 DBC
  - [ ] Implement BSM mirror alert control
  - [ ] Add `enableBsm` flag for HW1
  - [ ] Test blind spot detection accuracy

---

## Architecture and Code Quality

### 30. DBC Consolidation
- **Priority:** MEDIUM
- **Files:** `tesla_can.dbc`, `tesla_powertrain.dbc`
- **Issue:** HW1 uses legacy DBC files with different message addresses than HW2/HW3.
- **TODO:**
  - [ ] Audit all message differences between HW1 and HW2/HW3 DBCs
  - [ ] Create unified DBC with HW1-specific variants where needed
  - [ ] Document all HW1-specific message definitions
- **Unity Reference:** Unity's `tesla_can.dbc` is significantly more complete (33% larger, ~1486+ lines vs xnor's 931 lines). Missing from xnor's DBC (present in Unity) — operationally relevant: `ESP_ACC` (ID 293, long/lat acceleration from ESP), `ESP_145h` (ID 325, brake master cylinder pressure, standstill, wheel speed QF, espModeActive), `GTW_ESP1` (ID 520, ESP configuration from gateway), `DAS_object` (ID 777, lead vehicle tracking), `DAS_telemetry`/`DAS_telemetryM` (ID 937/938, lane telemetry). Panda-related: `GAS_COMMAND` (ID 1361), `GAS_SENSOR` (ID 1362), `ECU_BrakeCommand` (ID 1363), `ECU_BrakeStatus` (ID 1364), `IVS_Command` (ID 1365), `IVS_Status` (ID 1366). Diagnostic: `IBST_info` (ID 813), `IBST_dtcMatrix` (ID 861), `IBST_status` (ID 925). Other: `DAS_pscControl` (ID 537, autopark), `PARK_status2` (ID 782, ultrasonic sensors). **CRITICAL:** Unity's `DI_state` (ID 872) has `DI_digitalSpeed` at bit 32 (8 bits, scale 1) and `DI_cruiseSet` at bit 48 (8 bits, scale 1); xnor reverses these with `DI_cruiseSet` at bit 32 (9 bits, scale 0.5) and `DI_digitalSpeed` at bit 48 (8 bits, scale 1). Unity's `DAS_status` (ID 921, named `AutopilotStatus` in xnor) has `DAS_lssState` at bit 29 (3 bits) — removed in xnor, shifting `DAS_sideCollisionAvoid` from bit 32 to 30, `DAS_sideCollisionWarning` from 34 to 32, `DAS_sideCollisionInhibit` from 36 to 34. xnor adds `DAS_csaState` at bit 35 in this message (Unity has it in DAS_status2). Unity's `DAS_status2` (ID 905) has `DAS_relaxCruiseLimits` at bit 31 (1 bit) and `DAS_csaState` at bit 32 (2 bits) — both removed in xnor which instead places `DAS_lssState` at bit 31 (3 bits) in this message.

### 31. Code Path Consolidation
- **Priority:** MEDIUM
- **Files:** `carstate.py`, `carcontroller.py`, `teslacan_legacy.py`
- **Issue:** Separate parsing paths for HW1 vs HW2/HW3. Code duplication.
- **TODO:**
  - [ ] Identify common code paths between HW variants
  - [ ] Consolidate where possible
  - [ ] Add clear HW1-specific sections with documentation

### 32. Test Coverage
- **Priority:** HIGH
- **Files:** `tests/test_tesla.py`, `safety/tests/test_tesla_hw1.py`
- **Issue:** Limited test coverage for HW1-specific functionality.
- **TODO:**
  - [ ] Add HW1-specific unit tests for signal parsing
  - [ ] Add HW1 safety layer tests
  - [ ] Add integration tests for HW1 CAN messages
  - [ ] Test all HW1 TX messages

### 33. Documentation
- **Priority:** HIGH
- **Files:** README, comments
- **Issue:** Limited documentation of HW1-specific quirks and limitations.
- **TODO:**
  - [ ] Document all HW1 CAN message addresses
  - [ ] Document HW1 architecture limitations
  - [ ] Create hardware installation guide for HW1
  - [ ] Document known issues and workarounds
- **Unity Reference:** Unity uses a fundamentally different architecture: car code lives in `selfdrive/car/tesla/` (standard openpilot layout) rather than inside the opendbc submodule. Unity has 3 longitudinal control paths (pedal interceptor for PRE-AP, DAS_control for AP1, DAS_longControl for AP2) vs xnor's single DAS_control path. Unity has full IC cluster emulation via `HUD_module.py` (10+ fake DAS messages at various rates). Unity sends `DAS_object` (0x309, ID 777) at 10Hz for lead vehicle display on the factory cluster. Unity uses lookup-table-based steering rate limiting vs xnor's VehicleModel approach. Unity's DBC includes 17 additional messages not in xnor's DBC (ESP_ACC, ESP_145h, GTW_ESP1, DAS_object, GAS_COMMAND/SENSOR, ECU_BrakeCommand/Status, IBST_*, PARK_status2, DAS_telemetry, DAS_pscControl). Unity reads `ESP_ACC.Long_Acceleration`/`Lat_Acceleration` from the bus but does not use them for control decisions. Unity supports pedal interceptor (0x551, ID 1361) with full PID controller (PCC_module.py), pedal calibration pipeline, and iBooster brake-by-wire (ECU_BrakeCommand, ID 1363).

---

## Safety and Validation

### 34. Signal Plausibility Checks
- **Priority:** HIGH
- **Files:** `carstate.py`, `tesla_legacy.h`
- **Issue:** No checksum/counter validation on HW1. Need fallback signal validation.
- **TODO:**
  - [ ] Implement range checks for all critical signals
  - [ ] Implement rate-of-change checks
  - [ ] Implement cross-signal validation (e.g., speed vs wheel speed)
  - [ ] Add fault detection and fallback behavior

### 35. LKAS Passthrough Limitation
- **Priority:** MEDIUM
- **Files:** `tesla_legacy.h:17`
- **Issue:** TODO: Only LKAS (non-emergency) is currently supported since we've only seen it.
- **TODO:**
  - [ ] Investigate emergency steering messages on HW1
  - [ ] Implement emergency steering passthrough if needed
  - [ ] Test emergency scenarios

### 36. FSD 14 Support
- **Priority:** LOW
- **Files:** `values.py`, `tesla_legacy.h`
- **Issue:** FSD 14 flag not available for HW1.
- **TODO:**
  - [ ] Determine if FSD 14 is relevant for HW1
  - [ ] If yes, implement support
  - [ ] If no, document why

---

## HW1 Fixes - User Experience & Behavior

### 37. Restore TACC Behavior - 1 Pull vs 2 Pull Stalk
- **Priority:** HIGH
- **Issue:** Currently, pulling the cruise stalk once activates openpilot. On stock Tesla, 1 pull = TACC (Traffic Aware Cruise Control only), 2 pulls = TACC + Autosteer (LKAS). This change breaks user muscle memory and removes the ability to use TACC-only mode.
- **Current:** 1 stalk pull → openpilot (lat + long)
- **Stock:** 1 stalk pull → TACC (long only), 2 stalk pulls → TACC + Autosteer (lat + long)
- **Files:** `carstate.py`, `carcontroller.py`
- **Proposed Fix:**
  - [ ] Detect single stalk pull and pass through to stock Tesla for TACC activation
  - [ ] Trigger openpilot lateral control only on double pull (2nd pull within time window)
  - [ ] Maintain openpilot longitudinal when stock TACC is active (intercept accel commands)
  - [ ] Add UI indicator showing TACC-only vs TACC+LKAS state
  - [ ] Test stalk behavior matches stock Tesla timing (~0.5s window between pulls)
- **Unity Reference:** Unity parses `STW_ACTN_RQ` (ID 69) which includes `SpdCtrlLvr_Stat` (6-bit stalk state at bit 0 with values: FWD, RWD, UP_1ST, UP_2ND, DN_1ST, DN_2ND) and `TurnIndLvr_Stat`. Unity has dedicated cruise stalk state handling in `LONG_module.py` using `CS.cruise_buttons`. Unity also uses `STW_ANGL_STAT` (ID 3) and `STW_ANGLHP_STAT` (ID 14) for steering wheel angle. The `STW_ACTN_RQ` message at 0x2D (ID 69) is the primary stalk status source and is used in both forks.

### 38. Fix Autopark Not Working
- **Priority:** HIGH
- **Issue:** Autopark functionality does not work at all on HW1. openpilot likely intercepts steering/accel commands that autopark needs, or autopark state detection is broken.
- **Files:** `carstate.py:autopark`, `carcontroller.py`, `values.py`
- **Current:** Autopark state detected but not functional
- **Proposed Fix:**
  - [ ] Verify `DI_autoparkState` signal is parsed correctly on HW1 bus routing
  - [ ] Add autopark passthrough mode — release all steering/long control when autopark is active
  - [ ] Ensure `ret.cruiseState.enabled = False` during autopark
  - [ ] Test autopark activation from stock UI without openpilot interference
  - [ ] Add autopark fault handling (disable OP if autopark fails mid-sequence)
- **Unity Reference:** Unity has `DAS_pscControl` (0x219, ID 537) with `DAS_pscParkState` (4 bits, 15 states: NONE, PARK_LEFT_PARALLEL, PARK_LEFT_CROSS, PARK_RIGHT_PARALLEL, PARK_RIGHT_CROSS, PARALLEL_PULL_OUT_LEFT/RIGHT, SEARCH, PAUSE, SUMMON, ABORT, COMPLETE) and `DAS_eacState` (EAC state). Unity's `DAS_status` (0x399, ID 921) has `DAS_autoparkReady` (1 bit), `DAS_autoParked` (1 bit), `DAS_autoparkWaitingForBrake` (1 bit), `DAS_summonAvailable` (1 bit), `DAS_summonFwdLeashReached`/`DAS_summonRvsLeashReached` (1 bit each). xnor's `AutopilotStatus` (ID 921) has the same summon/autopark signals. Unity also reads `PARK_status2` (ID 782) for ultrasonic sensor data including curb type detection, SDI blind spot, and rack detection. Use `DAS_pscControl` and `DAS_status` signals to detect active autopark and suspend OP control.

### 39. Fix Summon Disconnecting Randomly
- **Priority:** MEDIUM
- **Issue:** Summon stops working randomly during use. Likely caused by openpilot CAN traffic interfering with the Tesla app's summon commands, or CAN bus arbitration conflicts.
- **Files:** `carstate.py`, `carcontroller.py`, `teslacan_legacy.py`
- **Proposed Fix:**
  - [ ] Detect summon active state (`DI_summon` or equivalent signal)
  - [ ] Suspend all openpilot CAN TX when summon is active
  - [ ] Do not rely on Tesla app for summon trigger — use native stalk/button input instead
  - [ ] Add summon state machine with clean entry/exit transitions
  - [ ] Test summon reliability with openpilot running in background
  - [ ] Consider rate-limiting openpilot CAN messages during summon to reduce bus load
- **Unity Reference:** Unity has summon state signals in `DAS_status` (ID 921): `DAS_summonObstacle`, `DAS_summonClearedGate`, `DAS_summonFwdLeashReached`, `DAS_summonRvsLeashReached`, `DAS_summonAvailable`. Unity also has `UI_driverAssistMapData` (ID 968) with `UI_parallelAutoparkEnabled`/`UI_perpendicularAutoparkEnabled` and `UI_driverAssistControl` (ID 1000) with `UI_summonHeartbeat`, `UI_summonExitType`, `UI_summonEntryType`, `UI_summonReverseDist`. Use these to detect when summon is active and suspend openpilot CAN TX completely (including DAS_steeringControl and DAS_control) to avoid bus conflicts.

### 40. Fix Speed Display Mismatch (Real vs Display Speed)
- **Priority:** MEDIUM
- **Issue:** openpilot uses raw CAN speed (`DI_vehicleSpeed`) which is the true vehicle speed. The Tesla dashboard displays a slightly lower "display speed" (typically 1-3 km/h lower for regulatory reasons). This causes openpilot's target speed to never match what the driver sees on the dash.
- **Files:** `carstate.py` (speed parsing), `carcontroller.py` (longitudinal control), `values.py` (speed calibration)
- **Current:** `ret.vEgoRaw = cp_chassis.vl["ESP_B"]["ESP_vehicleSpeed"] * CV.KPH_TO_MS`
- **Proposed Fix:**
  - [ ] Find the display speed signal in HW1 DBC (likely `GTW_speed` or similar)
  - [ ] If no display speed signal exists, apply a calibration factor (typically -1 to -3 km/h offset or ~2-3% scaling)
  - [ ] Create per-platform speed calibration table for HW1
  - [ ] Use display speed for cruise target setting and UI display
  - [ ] Keep real speed for safety-critical calculations (AEB, stopping distance)
  - [ ] Add `SP_SPEED_OFFSET` environment variable for user fine-tuning
  - [ ] Test across speed range (30-130 km/h) to verify consistent offset
- **Unity Reference:** The display speed signal IS available. Both Unity and xnor DBCs define `DI_digitalSpeed` in `DI_state` (ID 872) — this is the dashboard display speed (8 bits, scale 1.0, unit "speed"). **CRITICAL:** Unity has `DI_digitalSpeed` at bit 32 and `DI_cruiseSet` at bit 48. xnor reverses these: `DI_cruiseSet` at bit 32 and `DI_digitalSpeed` at bit 48. Verify the correct bit layout for your car, then read `DI_digitalSpeed` as the display-matched speed for cruise targets and UI. Keep `ESP_B.ESP_vehicleSpeed` for safety calculations.

---

## SunnyPilot-Specific Features (Not in Baseline openpilot)

### 41. 3-Finger Infotainment Touch Press (HAS_VEHICLE_BUS)
- **Priority:** MEDIUM
- **Files:** `sunnypilot/car/tesla/carstate_ext.py:30`, `sunnypilot/car/tesla/values.py:11`
- **Issue:** SunnyPilot detects 3-finger touch on the infotainment screen to toggle LKAS via `UI_status2.UI_activeTouchPoints` on the vehicle bus. HW1 may not have a separate vehicle bus or this signal.
- **TODO:**
  - [ ] Determine if HW1 has a vehicle CAN bus (separate from chassis/party bus)
  - [ ] If yes, verify `UI_status2` (0x3E8, ID 1000) exists and has `UI_activeTouchPoints`
  - [ ] Enable `HAS_VEHICLE_BUS` flag for HW1 platforms if supported
  - [ ] Test 3-finger touch detection on HW1 hardware

### 42. Cooperative Steering (COOP_STEERING)
- **Priority:** LOW
- **Files:** `sunnypilot/car/tesla/coop_steering.py`, `sunnypilot/car/tesla/values.py:12`
- **Issue:** SunnyPilot allows driver to override steering without disengaging openpilot (coop steering mode). Needs HW1-specific testing since HW1 uses angle-based steering (different behavior from torque-based).
- **TODO:**
  - [ ] Test coop steering on HW1 with angle-based steering control
  - [ ] Verify driver override detection works correctly (steering angle delta vs torque)
  - [ ] Tune override thresholds for HW1 if needed
  - [ ] Enable `COOP_STEERING` flag for HW1 platforms if tested successfully

### 43. Speed Limit Display from DAS_status
- **Priority:** MEDIUM
- **Files:** `sunnypilot/car/tesla/carstate_ext.py:38-49`, `tesla_can.dbc`
- **Issue:** SunnyPilot reads `DAS_status.DAS_fusedSpeedLimit` with unit detection from `DI_state.DI_speedUnits`. Requires both messages to exist and be correctly parsed on HW1.
- **TODO:**
  - [ ] Verify `DAS_status` (ID 921) and `DI_state` (ID 872) exist on HW1 bus
  - [ ] Confirm `DI_speedUnits` signal is at the correct bit position (verify xnor layout vs Unity)
  - [ ] Test speed limit display across speed ranges and unit changes (KPH/MPH)
  - [ ] Add speed limit source indicator (camera vs map vs none) if available

### 44. Extended FW Fingerprints
- **Priority:** LOW
- **Files:** `sunnypilot/car/tesla/fingerprints_ext.py`
- **Issue:** SunnyPilot maintains extended FW version fingerprints. HW1 firmware versions may differ from HW2/HW3 and need their own entries.
- **TODO:**
  - [ ] Collect HW1 firmware versions from real vehicles
  - [ ] Add HW1-specific FW fingerprints to `fingerprints_ext.py`
  - [ ] Verify HW1 fingerprint matching works end-to-end

---

## Quick Reference: File Locations

| File | Purpose | Key Lines |
|------|---------|-----------|
| `values.py` | Platform configs, safety flags | 43-118, 213-219, 232 |
| `carstate.py` | CAN state parsing | 18-24, 141, 158, 185-188, 249 |
| `carcontroller.py` | Steering/longitudinal control | 58, 76 |
| `interface.py` | Car interface, params setup | 54, 95 |
| `teslacan_legacy.py` | CAN packing for legacy | All |
| `tesla_legacy.h` | Legacy Tesla safety hooks | 17, 218-231, 241-249, 259-265, 277-279 |
| `tesla_can.dbc` | Legacy CAN messages | All |

---

## Priority Summary

| Priority | Count | Key Items |
|----------|-------|-----------|
| **CRITICAL** | 1 | DI_state bit layout |
| **HIGH** | 13 | APS_eacMonitor, EPS rate, DAS_status restructuring, checksums, external panda, gap adjust, HUD, SNG, tests, signal plausibility, docs, TACC stalk behavior, autopark |
| **MEDIUM** | 15 | ESP/Brake/DI_state signals, message addresses, TX expansion, LDW/FCW/lead display, invalid LKAS, PID tuning, actuator delay, lateral tuning, BSM, DBC consolidation, code consolidation, LKAS passthrough, summon, speed display mismatch |
| **LOW** | 11 | VCRIGHT_silla2, radar integration, wheel speed, steer ratio, jerk limits, transmission type, EV detection, FSD 14 |

---

## Comparison to Reference Platforms

### Toyota Has That Tesla HW1 Doesn't:
- Blind spot enable via fingerprint (`enableBsm`)
- Per-platform lateral torque tuning
- Per-platform longitudinal tuning (PID gains)
- Hybrid-specific actuator delays
- SmartDSU detection for longitudinal
- Radar-based vs camera-based ACC detection
- SECOC authentication
- Gap adjust button
- HUD control
- Lane departure warning
- Lead distance display
- FCW alert
- Auto resume SNG

### Honda Has That Tesla HW1 Doesn't:
- Per-platform lateral torque tuning
- Per-platform longitudinal PID tuning
- Manual transmission detection
- Hybrid detection
- Nidec vs Bosch architecture detection
- CANFD support
- Alt brake message detection
- Longitudinal actuator delay tuning
- Gap adjust button
- HUD control

### Hyundai Has That Tesla HW1 Doesn't:
- **Cluster/HUD display control** — Hyundai sends lane lines, warnings, and system state icons to the cluster via `LKAS11`/`LFAHDA`. Tesla HW1 sends nothing to its cluster.
- **AEB passthrough (ESCC)** — Hyundai forwards stock radar AEB/FCW commands through `SCC12` while OP controls longitudinal. Tesla loses stock AEB when OP is active.
- **Speed limit from navigation + camera** — Hyundai reads `SpeedLim_Nav_Clu` (nav) + `CF_Lkas_TsrSpeed_Display_Clu` (camera). Tesla has no speed limit reading at all.
- **Brake hold detection** — Hyundai reads `AVH_LAMP` (Auto Vehicle Hold). Tesla has no brake hold signal parsed.
- **Per-platform longitudinal tuning** — Hyundai has dynamic/predictive PID configs per platform. Tesla uses global hardcoded accel/jerk limits.
- **Checksum validation** — Hyundai supports CRC8 and 6B checksum schemes. Tesla HW1 ignores all checksums.
- **Multiple gas pedal types** — Hyundai detects EV/hybrid/ICE/FCEV gas signals. Tesla is always EV (single path).
- **SCC architecture detection** — Hyundai adapts to radar SCC / camera SCC / CAN FD variants. Tesla has one fixed architecture.
- **Steering torque control** — Hyundai uses torque-based LKAS with per-platform torque limits. Tesla uses angle-based steering (single global limit).
- **Non-SCC car support** — Hyundai supports cars without factory ACC. All Teslas have ACC.
- **Cancel button delay** — Hyundai delays cancel on brake press to avoid "SCC Conditions Not Met". Tesla has no equivalent.
- **ADAS ECU keep-alive** — Hyundai sends periodic messages to disabled ADAS ECU. Tesla has no ADAS ECU to manage.
- **Steering fault angle protection** — Hyundai limits MAX_ANGLE to 85° with consecutive frame tracking. Tesla uses model-based lateral acceleration limit.

---

## DBC Merge Reference (`dbc-merge` branch)

The `opendbc_repo` branch `dbc-merge` adds 9 Unity messages to xnor's `tesla_can.dbc`. Each commit maps to items in this TODO:

| Commit | Message(s) | Resolves / Relates To |
|--------|-----------|----------------------|
| `f223c78e` | ESP_145h (ID 325) | Items 2, 3 — brake pressure, standstill, wheel speed QF |
| `a3530afc` | ESP_ACC (ID 293) | Items 2, 3 — long/lat acceleration from ESP |
| `37382d96` | DAS_object (ID 777) | Item 17 — lead vehicle tracking for IC display |
| `ecf4a9eb` | GTW_ESP1 (ID 520) | Items 2, 3 — ESP configuration, hill start assist |
| `e01fa70b` | DAS_pscControl (ID 537) | Items 1, 38 — autopark state, EAC state |
| `be5a9541` | DAS_telemetry/DAS_telemetryM (IDs 937/938) | Items 14, 15 — lane telemetry, LDW |
| `c699ddd6` | PARK_status2 (ID 782) | Items 38, 39 — ultrasonic sensor status, SDI |
| `fe8cf0f0` | IBST_info/IBST_dtcMatrix/IBST_status (IDs 813/861/925) | Items 2, 3 — iBooster diagnostics |
| `b8dfef39` | CM_ conflict annotations | Items 5, 6 — documents xnor-vs-Unity bit layout diffs |

**Remaining:** Signal parsing (carstate.py), HUD implementation (carcontroller.py), safety layer updates (tesla_legacy.h), and hardware verification still needed.

---

## Notes

- HW1 uses `teslaLegacy` safety model with `FLAG_HW1`
- HW1 does NOT support `FLAG_EXTERNAL_PANDA`
- HW1 does NOT support `FSD_14` flag
- All HW1 messages have `ignore_checksum=true, ignore_counter=true`
- HW1 EPAS runs at 25 Hz (vs 100 Hz on HW3)
- HW1 chassis bus is 0 (HW3 uses bus 1)
- HW1 uses Bosch radar (HW3 uses Continental)
