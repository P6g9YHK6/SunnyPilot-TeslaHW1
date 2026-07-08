import json
import logging
import os
import time

from aiohttp import web

from openpilot.common.basedir import BASEDIR
from openpilot.system.hardware.hw import Paths
from cereal import messaging, log

logger = logging.getLogger("pitstop")


class DiagnosticMixin:

  def _get_car_list(self) -> dict:
    car_list_path = os.path.join(BASEDIR, "sunnypilot", "selfdrive", "car", "car_list.json")
    try:
      with open(car_list_path) as f:
        return json.load(f)
    except Exception:
      return {}

  def _parse_fingerprint_logs(self) -> dict:
    log_entries = self._read_swaglog(limit=100, search="fingerprinted")
    if log_entries:
      try:
        last_entry = log_entries[0]
        msg_raw = last_entry.get("msg", "{}")
        msg = json.loads(msg_raw) if isinstance(msg_raw, str) and msg_raw.startswith("{") else {}
        return {
          "ecu_count": msg.get("fw_count"),
          "vin": msg.get("vin"),
          "vin_rx_addr": msg.get("vin_rx_addr"),
          "vin_rx_bus": msg.get("vin_rx_bus"),
          "cached": msg.get("cached"),
          "fw_query_time_ms": int(msg.get("fw_query_time", 0) * 1000),
          "timestamp": last_entry.get("ts"),
        }
      except Exception:
        pass
    return {}

  async def handle_vehicle(self, request):
    bundle = self.params.get("CarPlatformBundle")
    platform_bundle = None
    if bundle:
      try:
        platform_bundle = json.loads(bundle) if isinstance(bundle, str) else bundle
      except Exception:
        platform_bundle = None
    fingerprint = None
    if self._device_state is not None:
      try:
        cp_bytes = self.params.get("CarParamsPersistent")
        if cp_bytes:
          from cereal import car
          cp = messaging.log_from_bytes(cp_bytes, car.CarParams)
          fingerprint = str(cp.carFingerprint) if cp.carFingerprint != "MOCK" else None
      except Exception:
        pass
    bundle_brand = platform_bundle.get("brand", "") if platform_bundle else ""
    if not bundle_brand and fingerprint:
      from cereal import car
      try:
        cp_bytes = self.params.get("CarParamsPersistent")
        if cp_bytes:
          cp = messaging.log_from_bytes(cp_bytes, car.CarParams)
          bundle_brand = str(cp.brand).lower() if cp.brand else ""
      except Exception:
        pass
    status = "unrecognized"
    if platform_bundle:
      status = "manual"
    elif fingerprint:
      status = "auto"
    return web.json_response({
      "brand": bundle_brand, "fingerprint": fingerprint,
      "platform_bundle": platform_bundle, "status": status,
      "is_offroad": self.params.get_bool("IsOffroad"),
    })

  async def handle_vehicle_platforms(self, request):
    platforms = self._get_car_list()
    return web.json_response(platforms)

  async def handle_vehicle_select(self, request):
    if request.method == "DELETE":
      self.params.remove("CarPlatformBundle")
      logger.info("[VEHICLE] platform removed")
      return web.json_response({"status": "ok", "removed": True})
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON")
    platform_name = body.get("platform")
    if not platform_name:
      raise web.HTTPBadRequest(text="Missing 'platform'")
    platforms = self._get_car_list()
    if platform_name not in platforms:
      raise web.HTTPNotFound(text=f"Platform '{platform_name}' not found")
    data = platforms[platform_name]
    self.params.put("CarPlatformBundle", {**data, "name": platform_name})
    logger.info(f"[VEHICLE] platform selected: {platform_name}")
    return web.json_response({"status": "ok", "platform": platform_name})

  async def handle_ignition_diagnostics(self, request):
    ds = self._device_state
    ignition_on = False
    ignition_line = False
    ignition_can = False
    pandas_connected = 0
    panda_timeout = False
    started = False

    if self._diag is not None:
      for proc in self._diag.get('processes', []):
        if 'pandad' in proc.get('name', '').lower():
          started = ds.started if ds else False

    panda_states = []
    try:
      sm = messaging.SubMaster(['pandaStates'])
      sm.update(0)
      if sm.seen['pandaStates']:
        for ps in sm['pandaStates']:
          if ps.pandaType != log.PandaState.PandaType.unknown:
            pandas_connected += 1
            ps_dict = {
              'ignition_line': bool(ps.ignitionLine),
              'ignition_can': bool(ps.ignitionCan),
              'panda_type': str(ps.pandaType).split('.')[-1] if ps.pandaType else None,
              'serial': str(ps.serial) if ps.serial else None,
              'voltage': ps.voltage,
              'temperature': ps.ambientTemp,
              'faults': list(ps.faults) if ps.faults else [],
            }
            panda_states.append(ps_dict)
            if ps.ignitionLine or ps.ignitionCan:
              ignition_on = True
            if ps.ignitionLine:
              ignition_line = True
            if ps.ignitionCan:
              ignition_can = True
      else:
        panda_timeout = True
    except Exception:
      panda_timeout = True

    thermal_status = "unknown"
    thermal_blocking = False
    if ds:
      thermal_status = str(ds.thermalStatus).split('.')[-1].lower()
      thermal_blocking = ds.thermalStatus in (log.DeviceState.ThermalStatus.overheated, log.DeviceState.ThermalStatus.critical)

    free_space_pct = None
    space_blocking = False
    if ds:
      free_space_pct = ds.freeSpacePercent
      space_blocking = free_space_pct < 5 if free_space_pct else False

    try:
      terms_accepted = self.params.get_bool("TermsAccepted")
    except Exception:
      terms_accepted = True
    terms_blocking = not terms_accepted

    try:
      offroad_mode = self.params.get_bool("OffroadMode")
    except Exception:
      offroad_mode = False
    offroad_blocking = offroad_mode

    panda_blocking = pandas_connected == 0
    startup_blocking = thermal_blocking or space_blocking or terms_blocking or offroad_mode or panda_blocking
    is_started = started and not offroad_mode and ignition_on and not startup_blocking
    ignition_source = "hardware" if ignition_line else ("can" if ignition_can else "none")

    time_online = None
    if started and ds and ds.startedMonoTime:
      try:
        time_online = int(time.monotonic() - (ds.startedMonoTime / 1e9))
      except Exception:
        pass

    def make_branch(num, condition, result, status, details=None, winner=False):
      return {"num": num, "condition": condition, "result": result,
              "status": status, "details": details or {}, "winner": winner}

    branches = []
    if panda_timeout:
      branches.append(make_branch(1, "if pandaStates received within 5s → CHECK_IGNITION else DISCONNECT",
        "DISCONNECT: No pandaStates received (timeout)", "failed",
        {"pandas_connected": 0, "panda_timeout": True, "timeout_ms": 5000}, winner=False))
      branches.append(make_branch(2, "if ignitionLine OR ignitionCan → IGNITION_ON else IGNITION_OFF",
        "NOT_EXECUTED (panda timeout)", "skipped", {}))
      branches.append(make_branch(3, "if CAN message received within 2s → IGNITION_CAN else RESET",
        "NOT_EXECUTED (panda timeout)", "skipped", {}))
      branches.append(make_branch(4, "if all startup_conditions AND ignition → START else BLOCK",
        "NOT_EXECUTED (panda timeout)", "skipped", {}))
    else:
      branches.append(make_branch(1, "if pandaStates received within 5s → CHECK_IGNITION else DISCONNECT",
        f"OK: {pandas_connected} panda(s) connected", "completed",
        {"pandas_connected": pandas_connected, "panda_timeout": False}, winner=False))
      if ignition_line:
        branches.append(make_branch(2, "if ignitionLine OR ignitionCan → IGNITION_ON else IGNITION_OFF",
          f"IGNITION_ON via hardware (ignitionLine=TRUE)", "winner",
          {"ignitionLine": True, "ignitionCan": ignition_can, "Combined": True}, winner=True))
        branches.append(make_branch(3, "if CAN message received within 2s → IGNITION_CAN else RESET",
          "OVERRIDDEN (ignitionLine already true)", "overridden", {"ignitionCan": ignition_can}))
      elif ignition_can:
        branches.append(make_branch(2, "if ignitionLine OR ignitionCan → IGNITION_ON else IGNITION_OFF",
          f"IGNITION_ON via CAN (ignitionCan=TRUE)", "winner",
          {"ignitionLine": False, "ignitionCan": True, "Combined": True}, winner=True))
        branches.append(make_branch(3, "if CAN message received within 2s → IGNITION_CAN else RESET",
          "USE_CAN: ignition via CAN message", "completed", {"ignitionCan": True, "ResetTimer": "not_expired"}))
      else:
        branches.append(make_branch(2, "if ignitionLine OR ignitionCan → IGNITION_ON else IGNITION_OFF",
          "IGNITION_OFF: no ignition detected", "failed",
          {"ignitionLine": False, "ignitionCan": ignition_can, "Combined": False}, winner=False))
        branches.append(make_branch(3, "if CAN message received within 2s → IGNITION_CAN else RESET",
          "NOT_EXECUTED (no ignition from hardware)", "skipped", {"ignitionCan": ignition_can}))
      if is_started:
        branches.append(make_branch(4, "if all startup_conditions AND ignition → START else BLOCK",
          f"START: deviceState.started=TRUE (all conditions met)", "winner",
          {"ignition_on": ignition_on, "thermal_status": thermal_status, "thermal_blocking": thermal_blocking,
           "free_space_pct": free_space_pct, "space_blocking": space_blocking, "terms_accepted": terms_accepted,
           "terms_blocking": terms_blocking, "offroad_mode": offroad_mode, "offroad_blocking": offroad_blocking,
           "panda_connected": pandas_connected > 0, "panda_blocking": panda_blocking,
           "startup_blocking": startup_blocking}, winner=True))
      elif startup_blocking:
        branches.append(make_branch(4, "if all startup_conditions AND ignition → START else BLOCK",
          f"BLOCKED: startup conditions not met", "failed",
          {"ignition_on": ignition_on, "thermal_status": thermal_status, "thermal_blocking": thermal_blocking,
           "free_space_pct": free_space_pct, "space_blocking": space_blocking, "terms_accepted": terms_accepted,
           "terms_blocking": terms_blocking, "offroad_mode": offroad_mode, "offroad_blocking": offroad_blocking,
           "panda_connected": pandas_connected > 0, "panda_blocking": panda_blocking,
           "startup_blocking": startup_blocking,
           "blocking_reasons": [r for r in ["thermal" if thermal_blocking else None,
             "space" if space_blocking else None, "terms" if terms_blocking else None,
             "offroad" if offroad_blocking else None, "panda" if panda_blocking else None] if r]},
          winner=False))
      else:
        branches.append(make_branch(4, "if all startup_conditions AND ignition → START else BLOCK",
          "WAITING: ignition off, waiting for car to start", "skipped",
          {"ignition_on": ignition_on, "startup_blocking": startup_blocking}))

    steps = []
    step_titles = {1: "Panda Connection", 2: "Hardware Ignition", 3: "CAN Ignition", 4: "Startup Conditions"}
    step_logic = {
      1: "if pandaStates received within 5s: CHECK_IGNITION else: DISCONNECT",
      2: "if ignitionLine OR ignitionCan: IGNITION_ON else: IGNITION_OFF",
      3: "if CAN message received within 2s: IGNITION_CAN else: RESET",
      4: "if all startup_conditions AND ignition: START else: BLOCK",
    }
    step_actions = {
      1: "Receive pandaStates from all connected pandas",
      2: "Check GPIO pin on panda harness (SBU1/SBU2 based on orientation)",
      3: "Check brand-specific CAN message for ignition state",
      4: "Check thermal, space, terms, offroad mode, panda connection",
    }
    for branch in branches:
      step_num = branch["num"]
      status = branch["status"]
      if status == "failed" and step_num == 1:
        failure_reasons = ["If USB cable disconnected → pandaStates not received",
          "If panda not powered → no response", "If CAN bus severed → panda can't relay"]
      elif status == "failed" and step_num == 2:
        failure_reasons = ["If harness not connected → ignitionLine=FALSE",
          "If car fully off → no voltage on ignition line", "If GPIO pin damaged → false reading"]
      elif status == "failed" and step_num == 4:
        failure_reasons = ["If thermal_status >= danger → START_BLOCKED",
          "If free_space < 5% → START_BLOCKED", "If terms not accepted → START_BLOCKED",
          "If offroad_mode = TRUE → deviceState.started stays FALSE"]
      else:
        failure_reasons = [] if status != "failed" else ["Condition not met"]
      steps.append({"id": step_num, "title": step_titles[step_num], "status": status,
        "winner": branch["winner"], "condition": step_logic[step_num],
        "action": step_actions[step_num], "result": branch["result"],
        "details": branch["details"], "failure_reasons": failure_reasons})

    history = []
    log_entries = self._read_swaglog(limit=50, search="ignition")
    for entry in log_entries:
      try:
        msg_raw = entry.get("msg", "")
        if isinstance(msg_raw, str) and "ignition" in msg_raw.lower():
          history.append({"ts": entry.get("ts"), "msg": msg_raw[:100]})
      except Exception:
        pass

    return web.json_response({
      "decision_tree": branches, "steps": steps,
      "result": {
        "status": "on" if ignition_on else ("blocked" if startup_blocking else "off"),
        "ignition_on": ignition_on, "device_started": is_started,
        "started_ts": ds.startedMonoTime / 1e9 if ds and ds.startedMonoTime else None,
        "time_online_s": time_online,
        "winner_branch": next((b["num"] for b in branches if b["winner"]), None),
        "source": ignition_source,
      },
      "panda_info": {
        "connected": pandas_connected > 0, "count": pandas_connected,
        "panda_states": panda_states,
      },
      "startup_conditions": {
        "thermal": {"status": thermal_status, "blocking": thermal_blocking},
        "space": {"free_pct": free_space_pct, "blocking": space_blocking},
        "terms": {"accepted": terms_accepted, "blocking": terms_blocking},
        "offroad": {"active": offroad_mode, "blocking": offroad_blocking},
        "panda": {"connected": pandas_connected > 0, "blocking": panda_blocking},
      },
      "history": history[:10],
    })

  async def handle_fingerprint_diagnostics(self, request):
    platform_bundle_raw = self.params.get("CarPlatformBundle")
    platform_bundle = None
    if platform_bundle_raw:
      try:
        platform_bundle = json.loads(platform_bundle_raw) if isinstance(platform_bundle_raw, str) else platform_bundle_raw
      except Exception:
        platform_bundle = None

    cache_raw = self.params.get("CarParamsCache")
    has_cache = cache_raw is not None
    persistent_raw = self.params.get("CarParamsPersistent")
    firmware_query_done = self.params.get_bool("FirmwareQueryDone")

    fingerprint = None
    source = None
    fuzzy_match = None
    vin = None
    brand = None
    dashcam_only = None
    passive = None
    safety_model = None
    dbc_names = None
    car_fw_count = 0

    if persistent_raw:
      try:
        from cereal import car
        cp = messaging.log_from_bytes(persistent_raw, car.CarParams)
        fingerprint = str(cp.carFingerprint) if cp.carFingerprint else None
        source = str(cp.fingerprintSource).split(".")[-1] if cp.fingerprintSource else None
        fuzzy_match = cp.fuzzyFingerprint
        vin = str(cp.carVin) if cp.carVin and cp.carVin != "VIN_UNKNOWN" else None
        brand = str(cp.brand).lower() if cp.brand else None
        dashcam_only = cp.dashcamOnly
        controller_available = self.params.get_bool("OpenpilotEnabledToggle") and not cp.dashcamOnly
        passive = cp.dashcamOnly or not controller_available
        if cp.safetyConfigs:
          safety_model = str(cp.safetyConfigs[0].safetyModel).split(".")[-1] if hasattr(cp.safetyConfigs[0], "safetyModel") else None
        car_fw_count = len(cp.carFw) if cp.carFw else 0
      except Exception:
        pass

    log_data = self._parse_fingerprint_logs()
    is_mock = fingerprint == "MOCK" or (fingerprint is None and source is None)
    is_cached = has_cache and firmware_query_done
    is_fixed = platform_bundle is not None

    def make_branch(num, condition, result, status, details=None, winner=False):
      return {"num": num, "condition": condition, "result": result,
              "status": status, "details": details or {}, "winner": winner}

    branches = []
    if is_fixed:
      branches.append(make_branch(1, "if fixed_fingerprint → USE_FIXED",
        f"USE_FIXED: {platform_bundle.get('platform') if platform_bundle else 'unknown'}", "winner",
        {"CarPlatformBundle": platform_bundle.get("platform"), "FINGERPRINT_ENV": os.environ.get("FINGERPRINT", "")}, winner=True))
    else:
      branches.append(make_branch(1, "if fixed_fingerprint → USE_FIXED else continue",
        "SKIP (no fixed_fingerprint set)", "skipped",
        {"CarPlatformBundle": platform_bundle, "FINGERPRINT_ENV": os.environ.get("FINGERPRINT", "")}))
      if is_cached:
        cached_source = source or "unknown"
        branches.append(make_branch(2, "if cached_params valid → USE_CACHED else RUN_FRESH_QUERY",
          f"USE_CACHED: fingerprint obtained from previous boot via {cached_source}",
          "winner" if not is_fixed else "overridden",
          {"cached_fingerprint": fingerprint, "cached_source": cached_source,
           "cached_vin": vin, "cached_ecus": car_fw_count}, winner=True))
        branches.append(make_branch(3, "if fw_candidates == 1 → USE_FW else continue",
          "NOT_EXECUTED (using cached from Step 2)", "skipped", {}))
        branches.append(make_branch(4, "if CAN_candidates == 1 → USE_CAN else MOCK",
          "NOT_EXECUTED (using cached from Step 2)", "skipped", {}))
      else:
        branches.append(make_branch(2, "if cached_params valid → USE_CACHED else RUN_FRESH_QUERY",
          "RUN_FRESH_QUERY (no valid cache)", "skipped",
          {"has_cache": has_cache, "firmware_query_done": firmware_query_done}))
        fw_candidates = log_data.get("ecu_count")
        if source == "fw":
          branches.append(make_branch(3, "if fw_candidates == 1 → USE_FW else continue",
            f"USE_FW: {fingerprint}", "winner",
            {"ecu_count": log_data.get("ecu_count"), "vin": log_data.get("vin") or vin,
             "vin_obtained": log_data.get("vin") is not None, "exact_fw_match": True,
             "fw_query_time_ms": log_data.get("fw_query_time_ms", 0)}, winner=True))
          branches.append(make_branch(4, "if CAN_candidates == 1 → USE_CAN else MOCK",
            "OVERRIDDEN by Step 3 (FW had exactly 1 candidate)", "overridden", {}))
        else:
          branches.append(make_branch(3, "if fw_candidates == 1 → USE_FW else continue",
            f"SKIP (fw_candidates={fw_candidates or 'N/A'}, not exactly 1)", "overridden",
            {"ecu_count": log_data.get("ecu_count"), "vin": log_data.get("vin") or vin,
             "vin_obtained": log_data.get("vin") is not None,
             "fw_query_time_ms": log_data.get("fw_query_time_ms", 0)}))
          if source == "can":
            branches.append(make_branch(4, "if CAN_candidates == 1 → USE_CAN else MOCK",
              f"USE_CAN: {fingerprint}", "winner",
              {"can_candidates_before": "~500 (all legacy fingerprints)",
               "can_candidates_after": "1", "fuzzy_match": fuzzy_match}, winner=True))
          else:
            branches.append(make_branch(4, "if CAN_candidates == 1 → USE_CAN else MOCK",
              "MOCK_FALLBACK: No candidates matched", "failed",
              {"can_candidates_after": "0", "reason": "No fingerprint match found"}))

    steps = []
    step_titles = {1: "Manual Selection", 2: "Cached CarParams", 3: "Firmware Query", 4: "CAN Fingerprint"}
    step_logic = {
      1: "if fixed_fingerprint: USE_FIXED else continue",
      2: "if cached_params valid: USE_CACHED else RUN_FRESH_QUERY",
      3: "if fw_candidates == 1: USE_FW else continue",
      4: "if CAN_candidates == 1: USE_CAN else MOCK",
    }
    step_actions = {
      1: "Check if CarPlatformBundle or FINGERPRINT env is set",
      2: "Check CarParamsCache exists and is valid for this car",
      3: "Query ECUs for firmware versions and match to known cars",
      4: "Collect CAN messages and eliminate incompatible vehicles",
    }
    for branch in branches:
      step_num = branch["num"]
      steps.append({"id": step_num, "title": step_titles[step_num], "status": branch["status"],
        "winner": branch["winner"], "condition": step_logic[step_num], "action": step_actions[step_num],
        "result": branch["result"], "details": branch["details"],
        "failure_reasons": [
          f"Step {step_num} would fail if: {failure}" for failure in
          ["condition not met" if not branch["winner"] else "N/A",
           "would cause fallback to next step" if not branch["winner"] else "N/A"]
        ] if not branch["winner"] else []})

    cached_historical = None
    if has_cache and source:
      cached_historical = {
        "note": "This fingerprint was obtained from a PREVIOUS boot's full fingerprinting flow",
        "source_step": f"Step {source == 'fw' and 3 or source == 'can' and 4 or source == 'fixed' and 1}",
        "source": source, "fingerprint": fingerprint, "vin": vin,
        "ecus": car_fw_count, "fuzzy": fuzzy_match,
      }

    result_status = "mock" if is_mock else ("manual" if is_fixed else ("cached" if is_cached else "fingerprinted"))

    try:
      dbc_names = list(self._can_handler.dbc.keys()) if self._can_handler.dbc else None
    except Exception:
      pass

    return web.json_response({
      "decision_tree": branches, "steps": steps,
      "cached_historical": cached_historical,
      "result": {
        "status": result_status,
        "fingerprint": fingerprint if fingerprint and fingerprint != "MOCK" else None,
        "source": source, "winner_branch": next((b["num"] for b in branches if b["winner"]), None),
        "is_fuzzy_match": fuzzy_match, "vin": vin, "brand": brand,
      },
      "platform_info": {
        "brand": brand, "safety_model": safety_model,
        "dashcam_only": dashcam_only, "passive": passive,
        "dbc_names": dbc_names,
      },
    })
