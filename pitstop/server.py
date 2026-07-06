import hashlib
import json
import logging
import os
import subprocess
import threading
import time

from aiohttp import web

from openpilot.common.params import Params, ParamKeyType, ParamKeyFlag
from openpilot.system.hardware.hw import Paths
from openpilot.system.version import get_build_metadata
from openpilot.sunnypilot.sunnylink.capabilities import generate_capabilities
from openpilot.sunnypilot.sunnylink.tools.generate_settings_schema import generate_schema
from openpilot.sunnypilot.models.fetcher import ModelFetcher
from openpilot.sunnypilot.models.helpers import get_active_bundle
from openpilot.sunnypilot.models.model_name import DEFAULT_MODEL
from openpilot.selfdrive.controls.lib.can_api.handler import CanApiHandler
from openpilot.pitstop.schema import generate_openapi_schema

from cereal import messaging, custom

logger = logging.getLogger("pitstop")

HOST = "0.0.0.0"
PORT = 8080
EXTERNAL_PORT = 80  # iptables redirects :80 → :PORT

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
PARAMS_METADATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sunnypilot", "sunnylink", "params_metadata.json")
PITSTOP_DATA_DIR = "/data/pitstop"
BACKUP_DIR_NAME = "backups"

SWAGGER_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>PitStop API Docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css">
  <style>body{margin:0}</style>
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
<script>
SwaggerUIBundle({
  url: "/openapi.json",
  dom_id: "#swagger-ui",
  presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
  layout: "BaseLayout",
  deepLinking: true,
})
</script>
</body>
</html>"""


@web.middleware
async def access_log_middleware(request, handler):
  if request.path == "/api/logs":
    return await handler(request)
  t0 = time.time()
  try:
    response = await handler(request)
    elapsed = (time.time() - t0) * 1000
    if request.path.startswith("/api/"):
      status = response.status
      msg = f"[{status}] {request.method} {request.path} ({elapsed:.0f}ms)"
      if status >= 500:
        logger.error(msg)
      elif status >= 400:
        logger.warning(msg)
      else:
        logger.info(msg)
    return response
  except web.HTTPException as ex:
    elapsed = (time.time() - t0) * 1000
    if request.path.startswith("/api/"):
      logger.warning(f"[{ex.status}] {request.method} {request.path} ({elapsed:.0f}ms)")
    raise
  except Exception:
    elapsed = (time.time() - t0) * 1000
    if request.path.startswith("/api/"):
      logger.exception(f"[500] {request.method} {request.path} ({elapsed:.0f}ms)")
    raise


class PitStopServer:
  # Key services selfdrived monitors (subset — excludes sensors/GPS/ignored)
  _WATCHED_SERVICES = [
    'liveCalibration', 'livePose', 'liveParameters', 'longitudinalPlan',
    'modelV2', 'cameraOdometry', 'driverMonitoringState',
    'liveTorqueParameters', 'radarState', 'liveDelay',
  ]

  def __init__(self):
    self.params = Params()
    self._can_handler = CanApiHandler()
    self._running = True
    self._model_state = None
    self._device_state = None
    self._diag = None   # cached diagnostic snapshot
    self._gps_location = None
    self._calibration = None
    self._speed_data = None
    self._is_engaged = False
    self._static_version = self._hash_static()
    for target in (
      self._model_manager_loop,
      self._device_state_loop,
      self._diag_loop,
      self._gps_location_loop,
    ):
      threading.Thread(target=target, daemon=True).start()

  @staticmethod
  def _hash_static():
    h = hashlib.md5()
    for f in ('app.js', 'index.html', 'style.css'):
      p = os.path.join(STATIC_DIR, f)
      try:
        with open(p, 'rb') as fh:
          h.update(fh.read())
      except FileNotFoundError:
        pass
    return h.hexdigest()[:8]

  def _subscriber_loop(self, topic, attr, field):
    logger.info(f"[LOOP] {topic} subscriber started")
    try:
      sock = messaging.sub_sock(topic, conflate=True, timeout=1000)
      while self._running:
        msg = messaging.recv_one(sock)   # blocks up to 1s — zero CPU when idle
        if msg is not None:
          setattr(self, attr, getattr(msg, field))
    except Exception:
      logger.warning(f"{topic} subscriber not available")
    logger.info(f"[LOOP] {topic} subscriber stopped")

  def _model_manager_loop(self):
    self._subscriber_loop('modelManagerSP', '_model_state', 'modelManagerSP')

  def _device_state_loop(self):
    self._subscriber_loop('deviceState', '_device_state', 'deviceState')

  def _gps_location_loop(self):
    self._subscriber_loop('gpsLocationExternal', '_gps_location', 'gpsLocationExternal')

  def _diag_loop(self):
    """Single background thread for service health, active alert, and process list."""
    logger.info("[LOOP] diagnostic monitor started")
    try:
      sm = messaging.SubMaster(self._WATCHED_SERVICES + ['selfdriveState', 'managerState', 'carState', 'longitudinalPlanSP', 'liveMapDataSP', 'carStateSP', 'selfdriveStateSP'])
      while self._running:
        sm.update(2000)
        services = []
        for s in self._WATCHED_SERVICES:
          readers = self._msgq_readers(s)
          services.append({
            'name': s,
            'valid': bool(sm.valid[s]),
            'alive': bool(sm.alive[s]),
            'freq_ok': bool(sm.freq_ok[s]),
            'readers': readers,
          })
        sd = sm['selfdriveState']
        alert = {
          'text1': str(sd.alertText1),
          'text2': str(sd.alertText2),
          'status': str(sd.alertStatus).split('.')[-1],
          'type': str(sd.alertType),
        } if sm.seen['selfdriveState'] else None
        self._is_engaged = bool(sd.enabled) if sm.seen['selfdriveState'] else False
        processes = []
        if sm.seen['managerState']:
          for p in sm['managerState'].processes:
            processes.append({
              'name': str(p.name),
              'running': bool(p.running),
              'should_run': bool(p.shouldBeRunning),
            })
        self._diag = {
          'services': services,
          'services_ok': all(s['valid'] and s['alive'] and s['freq_ok'] for s in services),
          'alert': alert,
          'processes': processes,
        }
        if sm.updated['liveCalibration']:
          lc = sm['liveCalibration']
          self._calibration = {
            'status': str(lc.calStatus).split('.')[-1],
            'percent': lc.calPerc,
            'valid_blocks': lc.validBlocks,
            'pitch': lc.rpyCalib[0] if len(lc.rpyCalib) > 0 else None,
            'roll': lc.rpyCalib[1] if len(lc.rpyCalib) > 1 else None,
            'yaw': lc.rpyCalib[2] if len(lc.rpyCalib) > 2 else None,
          }
        # speed data
        cs = sm['carState'] if sm.seen['carState'] else None
        lp = sm['longitudinalPlan'] if sm.seen['longitudinalPlan'] else None
        radar = sm['radarState'] if sm.seen['radarState'] else None
        lpsp = sm['longitudinalPlanSP'] if sm.seen['longitudinalPlanSP'] else None
        mapsp = sm['liveMapDataSP'] if sm.seen['liveMapDataSP'] else None
        cssp = sm['carStateSP'] if sm.seen['carStateSP'] else None
        sdsps = sm['selfdriveStateSP'] if sm.seen['selfdriveStateSP'] else None

        lead = None
        if radar is not None:
          ld = radar.leadOne
          if ld is not None:
            lead = {"vLead": ld.vLead, "vLeadK": ld.vLeadK, "vRel": ld.vRel, "dRel": ld.dRel}

        plan_sp = None
        if lpsp is not None:
          plan_sp = {"vTarget": lpsp.vTarget}
          if lpsp.smartCruiseControl is not None:
            plan_sp["sccVisionVTarget"] = lpsp.smartCruiseControl.vision.vTarget
            plan_sp["sccMapVTarget"] = lpsp.smartCruiseControl.map.vTarget
          if lpsp.speedLimit is not None:
            plan_sp["speedLimitAssistVTarget"] = lpsp.speedLimit.assist.vTarget

        slr = lpsp.speedLimit.resolver if lpsp is not None and lpsp.speedLimit is not None else None

        icbm_vtarget = None
        if sdsps is not None and sdsps.intelligentCruiseButtonManagement is not None:
          icbm_vtarget = sdsps.intelligentCruiseButtonManagement.vTarget

        self._speed_data = {
          "ego": {
            "speed": cs.vEgo if cs else None,
            "aEgo": cs.aEgo if cs else None,
            "standstill": cs.standstill if cs else None,
          },
          "cruise": {
            "setSpeed": cs.vCruise if cs else None,
            "clusterSpeed": cs.vCruiseCluster if cs else None,
          },
          "wheels": {
            k: getattr(cs.wheelSpeeds, k) if cs else None
            for k in ("fl", "fr", "rl", "rr")
          } if cs else None,
          "lead": lead,
          "plan": {
            "vTarget": lp.vTarget if lp is not None else None,
            "vCruise": lp.vCruise if lp is not None else None,
            "vMax": lp.vMax if lp is not None else None,
            "vCurvature": lp.vCurvature if lp is not None else None,
            "aTarget": lp.aTarget if lp is not None else None,
          },
          "planSP": plan_sp,
          "limit": {
            "speedLimit": slr.speedLimit if slr is not None else None,
            "speedLimitFinal": slr.speedLimitFinal if slr is not None else None,
            "speedLimitOffset": slr.speedLimitOffset if slr is not None else None,
            "distToSpeedLimit": slr.distToSpeedLimit if slr is not None else None,
            "valid": slr.speedLimitValid if slr is not None else None,
          },
          "map": {
            "speedLimit": mapsp.speedLimit if mapsp is not None else None,
            "valid": mapsp.speedLimitValid if mapsp is not None else None,
            "speedLimitAhead": mapsp.speedLimitAhead if mapsp is not None else None,
            "aheadValid": mapsp.speedLimitAheadValid if mapsp is not None else None,
            "aheadDist": mapsp.speedLimitAheadDistance if mapsp is not None else None,
          },
          "carSpeedLimit": cssp.speedLimit if cssp is not None else None,
          "icbmVtarget": icbm_vtarget,
        }
    except Exception:
      logger.warning("diag loop error", exc_info=True)

  @staticmethod
  def _msgq_readers(name):
    """Read num_readers from msgq shared memory (first 8 bytes, uint64 LE)."""
    try:
      import struct
      with open(f'/dev/shm/msgq_{name}', 'rb') as f:
        return struct.unpack('<Q', f.read(8))[0]
    except Exception:
      return None

  async def handle_diag(self, request):
    if self._diag is None:
      return web.json_response({"error": "no diag data"}, status=503)
    return web.json_response(self._diag)

  # ---- New endpoints (GPS / Calibration / Network / Sunnylink / Storage) ----

  async def handle_gps(self, request):
    g = self._gps_location
    if g is None:
      return web.json_response({"error": "no gps fix"}, status=503)
    return web.json_response({
      "latitude": g.latitude,
      "longitude": g.longitude,
      "altitude": g.altitude,
      "speed": g.speed,
      "bearing": g.bearingDeg,
      "accuracy": g.horizontalAccuracy,
      "vertical_accuracy": g.verticalAccuracy,
      "bearing_accuracy": g.bearingAccuracyDeg,
      "speed_accuracy": g.speedAccuracy,
      "has_fix": g.hasFix,
      "satellites": g.satelliteCount,
      "source": str(g.source).split('.')[-1],
    })

  async def handle_calibration(self, request):
    if self._calibration is None:
      return web.json_response({"error": "no calibration data"}, status=503)
    return web.json_response(self._calibration)

  async def handle_network(self, request):
    ds = self._device_state
    if ds is None:
      return web.json_response({"error": "no device state"}, status=503)

    result = {
      "type": str(ds.networkType).split('.')[-1],
      "strength": str(ds.networkStrength).split('.')[-1],
      "metered": bool(ds.networkMetered),
    }

    try:
      ni = ds.networkInfo
      result["tech"] = str(ni.technology) if ni.technology else None
      result["net_state"] = str(ni.state) if ni.state else None
    except Exception:
      pass

    try:
      ns = ds.networkStats
      result["wwanTx"] = ns.wwanTx
      result["wwanRx"] = ns.wwanRx
    except Exception:
      pass

    try:
      ping_ns = ds.lastAthenaPingTime
      if ping_ns:
        result["last_athena_ping"] = max(0, int((time.monotonic_ns() - ping_ns) / 1_000_000_000))
    except Exception:
      pass

    # Device IP / gateway (fast shell commands)
    try:
      ip_out = subprocess.run(["ip", "-4", "addr", "show", "scope", "global"], capture_output=True, text=True, timeout=3)
      for line in ip_out.stdout.split('\n'):
        parts = line.strip().split()
        if parts and parts[0] == 'inet':
          result["device_ip"] = parts[1].split('/')[0]
          break
    except Exception:
      pass

    try:
      gw_out = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, timeout=3)
      for line in gw_out.stdout.split('\n'):
        parts = line.strip().split()
        if len(parts) >= 3:
          result["gateway"] = parts[2]
          break
    except Exception:
      pass

    try:
      mac_out = subprocess.run(["cat", "/sys/class/net/wlan0/address"], capture_output=True, text=True, timeout=3)
      mac = mac_out.stdout.strip()
      if mac:
        result["mac"] = mac
    except Exception:
      pass

    # Hotspot info
    hotspot = {"active": False}
    try:
      active = subprocess.run(["nmcli", "-t", "connection", "show", "--active"], capture_output=True, text=True, timeout=3)
      hotspot["active"] = "Hotspot:" in active.stdout
    except Exception:
      pass

    if hotspot["active"]:
      try:
        show = subprocess.run(["nmcli", "-s", "-t", "connection", "show", "Hotspot"], capture_output=True, text=True, timeout=3)
        for line in show.stdout.split('\n'):
          if line.startswith("802-11-wireless.ssid:"):
            hotspot["ssid"] = line.split(':', 1)[1].strip()
          elif line.startswith("802-11-wireless-security.psk:"):
            hotspot["password"] = line.split(':', 1)[1].strip()
      except Exception:
        pass

      hotspot["gateway"] = "100.100.0.1"

      try:
        with open("/var/lib/misc/dnsmasq.leases") as f:
          data = f.read().strip()
          hotspot["clients"] = len([l for l in data.split('\n') if l]) if data else 0
      except FileNotFoundError:
        try:
          with open("/var/lib/NetworkManager/dnsmasq-wlan0.leases") as f:
            data = f.read().strip()
            hotspot["clients"] = len([l for l in data.split('\n') if l]) if data else 0
        except FileNotFoundError:
          try:
            arp = subprocess.run(["ip", "neigh", "show", "dev", "wlan0"], capture_output=True, text=True, timeout=3)
            hotspot["clients"] = len([l for l in arp.stdout.split('\n') if 'REACHABLE' in l])
          except Exception:
            hotspot["clients"] = 0
      except Exception:
        hotspot["clients"] = 0

    result["hotspot"] = hotspot
    return web.json_response(result)

  async def handle_sunnylink(self, request):
    def _gp(key):
      v = self.params.get(key)
      return v.decode() if isinstance(v, bytes) else v
    enabled = self.params.get_bool("SunnylinkEnabled")
    dongle_id = _gp("SunnylinkDongleId")
    registered = bool(dongle_id)
    last_ping = self.params.get("LastSunnylinkPingTime")
    temp_fault = self.params.get_bool("SunnylinkTempFault")
    online = False
    if last_ping is not None:
      try:
        last_ping_ns = int(last_ping)
        online = (time.time_ns() - last_ping_ns) < 80_000_000_000
      except (ValueError, AttributeError, OverflowError):
        pass
    return web.json_response({
      "enabled": enabled,
      "registered": registered,
      "dongle_id": dongle_id,
      "online": online,
      "temp_fault": temp_fault,
      "ready": enabled and registered and not temp_fault,
    })

  async def handle_storage(self, request):
    def _usage(path):
      try:
        s = os.statvfs(path)
        total = s.f_frsize * s.f_blocks
        free = s.f_frsize * s.f_bfree
        used = total - free
        return {"total": total, "used": used, "free": free, "pct": round(used / total * 100, 1) if total else 0}
      except Exception:
        return None
    return web.json_response({
      "root": _usage("/"),
      "data": _usage("/data") if os.path.isdir("/data") else None,
      "logs": _usage(Paths.log_root()),
      "models": _usage(Paths.model_root()),
      "crashes": _usage(Paths.crash_log_root()),
    })

  async def handle_speeds(self, request):
    if self._speed_data is None:
      return web.json_response({"error": "no speed data"}, status=503)
    return web.json_response(self._speed_data)

  # ---- System ----

  async def handle_telemetry(self, request):
    cs = None
    cp = None
    ds = self._device_state
    try:
      gear = str(cs.gearShifter) if cs is not None else None
      # capnp enum stringifies as "GearShifter.drive" etc. — strip prefix
      if gear and '.' in gear:
        gear = gear.split('.')[-1]
    except Exception:
      gear = None
    try:
      net_type = str(ds.networkType).split('.')[-1] if ds is not None else None
    except Exception:
      net_type = None
    try:
      thermal = str(ds.thermalStatus).split('.')[-1] if ds is not None else None
    except Exception:
      thermal = None
    return web.json_response({
      "ignition": bool(ds.started) if ds is not None else None,
      "started": bool(ds.started) if ds is not None else None,
      "car": {
        "brand": str(cp.brand) if cp is not None else None,
        "fingerprint": str(cp.carFingerprint) if cp is not None else None,
        "vin": str(cp.carVin) if cp is not None else None,
      },
      "motion": {
        "speed_ms": float(cs.vEgo) if cs is not None else None,
        "gear": gear,
        "standstill": bool(cs.standstill) if cs is not None else None,
      },
      "device": {
        "temp_c": float(ds.maxTempC) if ds is not None else None,
        "memory_pct": float(ds.memoryUsagePercent) if ds is not None else None,
        "cpu_pct": float(ds.cpuUsagePercent[0]) if ds is not None and len(ds.cpuUsagePercent) > 0 else None,
        "free_space_pct": float(ds.freeSpacePercent) if ds is not None else None,
        "network_type": net_type,
        "thermal_status": thermal,
      },
    })

  async def handle_status(self, request):
    return web.json_response({
      "enabled": self.params.get_bool("PitStopEnabled"),
      "is_offroad": self.params.get_bool("IsOffroad"),
      "is_metric": self.params.get_bool("IsMetric"),
      "engaged": self._is_engaged,
      "version": 1,
      "webVersion": self._static_version,
    })

  async def handle_device(self, request):
    def _getstr(key):
      v = self.params.get(key)
      return v.decode("utf-8", errors="replace") if isinstance(v, bytes) else (v or "")

    dongle_id = _getstr("DongleId")
    hardware_serial = _getstr("HardwareSerial")
    try:
      build = get_build_metadata()
      version = build.openpilot.version
      branch = build.channel
      git_commit = build.openpilot.git_commit
      raw_date = (build.openpilot.git_commit_date or '').strip("'")
      # format: "1782947217 2026-07-02 01:06:57 +0200" — drop the epoch prefix
      date_parts = raw_date.split(' ')
      git_commit_date = ' '.join(date_parts[1:]) if len(date_parts) > 1 else raw_date
      is_dirty = build.openpilot.is_dirty
      git_origin = build.openpilot.git_normalized_origin
      git_repo = '/'.join(git_origin.split('/')[1:]) if '/' in git_origin else git_origin
    except Exception:
      version = _getstr("Version")
      branch = None
      git_commit = None
      git_commit_date = None
      is_dirty = None
      git_repo = None

    return web.json_response({
      "dongle_id": dongle_id,
      "hardware_serial": hardware_serial,
      "version": version,
      "branch": branch,
      "git_commit": git_commit,
      "git_commit_date": git_commit_date,
      "git_repo": git_repo,
      "is_dirty": is_dirty,
    })

  # ---- Params ----

  async def handle_params_list(self, request):
    try:
      keys = sorted(k.decode("utf-8") for k in self.params.all_keys())
      return web.json_response({k: {} for k in keys})
    except Exception:
      return web.json_response({"error": "failed to list params"}, status=500)

  def _param_to_str(self, raw) -> str:
    """Normalize any params.get() return value to a string the UI can use."""
    if isinstance(raw, bool):
      return "1" if raw else "0"
    if isinstance(raw, bytes):
      return raw.decode("utf-8", errors="replace")
    if isinstance(raw, (int, float)):
      return str(raw)
    if isinstance(raw, (dict, list)):
      return json.dumps(raw)
    return str(raw) if raw is not None else ""

  def _smart_put(self, key: str, str_value: str):
    """Write str_value into a param, converting to the right Python type."""
    try:
      current = self.params.get(key)
    except Exception as e:
      raise ValueError(f"Unknown param '{key}'") from e

    sv = str(str_value)
    if isinstance(current, bool) or (current is None and sv in ("0", "1")):
      self.params.put_bool(key, sv in ("1", "true", "yes"))
      logger.debug(f"[PARAM] {key} -> bool({sv in ('1', 'true', 'yes')})")
    elif isinstance(current, int):
      self.params.put(key, int(sv))
      logger.debug(f"[PARAM] {key} -> int({sv})")
    elif isinstance(current, float):
      self.params.put(key, float(sv))
      logger.debug(f"[PARAM] {key} -> float({sv})")
    elif isinstance(current, (dict, list)):
      self.params.put(key, json.loads(sv))
      logger.debug(f"[PARAM] {key} -> json({sv})")
    elif isinstance(current, bytes):
      self.params.put(key, sv.encode("utf-8"))
      logger.debug(f"[PARAM] {key} -> bytes({sv})")
    elif current is None:
      ptype = self.params.get_type(key)
      if ptype == ParamKeyType.FLOAT:
        self.params.put(key, float(sv))
        logger.debug(f"[PARAM] {key} -> float({sv}) (type=FLOAT)")
      elif ptype == ParamKeyType.INT:
        self.params.put(key, int(sv))
        logger.debug(f"[PARAM] {key} -> int({sv}) (type=INT)")
      elif ptype == ParamKeyType.BOOL:
        self.params.put_bool(key, sv in ("1", "true", "yes"))
        logger.debug(f"[PARAM] {key} -> bool({sv in ('1', 'true', 'yes')}) (type=BOOL)")
      else:
        self.params.put(key, sv)
        logger.debug(f"[PARAM] {key} -> str({sv}) (type=other)")
    else:
      self.params.put(key, sv)
      logger.debug(f"[PARAM] {key} -> str({sv}) (fallback)")

  async def handle_param_get(self, request):
    key = request.match_info.get("key")
    try:
      raw = self.params.get(key)
    except Exception:
      raise web.HTTPNotFound(text=f"Unknown param '{key}'") from None
    if raw is None:
      return web.json_response({"key": key, "value": None})
    return web.json_response({"key": key, "value": self._param_to_str(raw)})

  async def handle_param_set(self, request):
    key = request.match_info.get("key")
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    value = body.get("value")
    if value is None:
      raise web.HTTPBadRequest(text="Missing 'value'")
    try:
      self._smart_put(key, str(value))
    except (ValueError, TypeError) as e:
      raise web.HTTPBadRequest(text=str(e)) from None
    logger.info(f"[PARAM] {key} = {value}")
    return web.json_response({"key": key, "status": "ok"})

  async def handle_param_put_bool(self, request):
    key = request.match_info.get("key")
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    value = body.get("value")
    if not isinstance(value, bool):
      raise web.HTTPBadRequest(text="'value' must be boolean")
    try:
      self.params.put_bool(key, value)
    except Exception as e:
      raise web.HTTPBadRequest(text=f"Cannot set '{key}': {e}") from None
    logger.info(f"[PARAM] {key} = {value} (bool)")
    return web.json_response({"key": key, "value": value, "status": "ok"})

  async def handle_param_put_int(self, request):
    key = request.match_info.get("key")
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    value = body.get("value")
    if not isinstance(value, (int, float)):
      raise web.HTTPBadRequest(text="'value' must be a number")
    try:
      self.params.put(key, int(value))
    except Exception as e:
      raise web.HTTPBadRequest(text=f"Cannot set '{key}': {e}") from None
    logger.info(f"[PARAM] {key} = {int(value)} (int)")
    return web.json_response({"key": key, "value": int(value), "status": "ok"})

  async def handle_param_put_float(self, request):
    key = request.match_info.get("key")
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    value = body.get("value")
    if not isinstance(value, (int, float)):
      raise web.HTTPBadRequest(text="'value' must be a number")
    try:
      self.params.put(key, float(value))
    except Exception as e:
      raise web.HTTPBadRequest(text=f"Cannot set '{key}': {e}") from None
    logger.info(f"[PARAM] {key} = {float(value)} (float)")
    return web.json_response({"key": key, "value": float(value), "status": "ok"})

  # ---- Settings ----

  async def handle_settings_schema(self, request):
    try:
      schema = generate_schema()
    except FileNotFoundError:
      raise web.HTTPNotFound(text="settings_ui.json not found") from None
    return web.json_response(schema)

  async def handle_capabilities(self, request):
    caps = generate_capabilities(self.params)
    return web.json_response(caps)

  # ---- Backup ----

  async def handle_backup_list(self, request):
    backup_dir = os.path.join(PITSTOP_DATA_DIR, BACKUP_DIR_NAME)
    backups = []
    if os.path.isdir(backup_dir):
      for fname in sorted(os.listdir(backup_dir)):
        fpath = os.path.join(backup_dir, fname)
        if os.path.isfile(fpath):
          info = {
            "name": fname,
            "size": os.path.getsize(fpath),
            "mtime": os.path.getmtime(fpath),
          }
          try:
            with open(fpath) as f:
              data = json.load(f)
              if "label" in data:
                info["label"] = data["label"]
          except Exception:
            pass
          backups.append(info)
    return web.json_response(backups)

  async def handle_backup_create(self, request):
    backup_dir = os.path.join(PITSTOP_DATA_DIR, BACKUP_DIR_NAME)
    os.makedirs(backup_dir, exist_ok=True)
    config = {}
    for k in self.params.all_keys(ParamKeyFlag.PERSISTENT):
      key = k.decode("utf-8")
      val = self.params.get(key)
      if val is not None:
        config[key] = val.hex() if isinstance(val, bytes) else str(val)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    fname = f"backup-{timestamp}.json"
    fpath = os.path.join(backup_dir, fname)
    with open(fpath, "w") as f:
      json.dump({"created": time.time(), "params": config}, f)
    logger.info(f"[BACKUP] created {fname} ({len(config)} params)")
    return web.json_response({"name": fname, "status": "created"})

  async def handle_backup_delete(self, request):
    name = request.match_info.get("name")
    if not name:
      raise web.HTTPBadRequest(text="Missing name")
    backup_dir = os.path.join(PITSTOP_DATA_DIR, BACKUP_DIR_NAME)
    fpath = os.path.normpath(os.path.join(backup_dir, name))
    if not fpath.startswith(backup_dir + os.sep):
      raise web.HTTPBadRequest(text="Invalid backup name")
    if not os.path.isfile(fpath):
      raise web.HTTPNotFound(text=f"Backup '{name}' not found")
    os.remove(fpath)
    logger.info(f"[BACKUP] deleted {name}")
    return web.json_response({"status": "deleted"})

  async def handle_backup_upload(self, request):
    backup_dir = os.path.join(PITSTOP_DATA_DIR, BACKUP_DIR_NAME)
    os.makedirs(backup_dir, exist_ok=True)
    reader = await request.multipart()
    field = await reader.next()
    if field is None or field.name != "file":
      raise web.HTTPBadRequest(text="Missing file field")
    filename = field.filename or f"backup-upload-{int(time.time())}.json"
    if not filename.endswith(".json"):
      filename += ".json"
    data = await field.read()
    try:
      parsed = json.loads(data)
    except json.JSONDecodeError:
      raise web.HTTPBadRequest(text="Invalid JSON file")
    if not isinstance(parsed, dict) or "params" not in parsed:
      raise web.HTTPBadRequest(text="Not a valid backup file (missing 'params')")
    fpath = os.path.normpath(os.path.join(backup_dir, filename))
    if not fpath.startswith(backup_dir + os.sep):
      raise web.HTTPBadRequest(text="Invalid filename")
    with open(fpath, "wb") as f:
      f.write(data)
    logger.info(f"[BACKUP] uploaded {filename} ({len(data)} bytes)")
    return web.json_response({"name": filename, "status": "uploaded"})

  async def handle_backup_set_label(self, request):
    name = request.match_info.get("name")
    if not name:
      raise web.HTTPBadRequest(text="Missing name")
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    label = body.get("label")
    if label is None:
      raise web.HTTPBadRequest(text="Missing 'label'")
    backup_dir = os.path.join(PITSTOP_DATA_DIR, BACKUP_DIR_NAME)
    fpath = os.path.normpath(os.path.join(backup_dir, name))
    if not fpath.startswith(backup_dir + os.sep):
      raise web.HTTPBadRequest(text="Invalid backup name")
    if not os.path.isfile(fpath):
      raise web.HTTPNotFound(text=f"Backup '{name}' not found")
    with open(fpath) as f:
      data = json.load(f)
    data["label"] = label
    with open(fpath, "w") as f:
      json.dump(data, f)
    logger.info(f"[BACKUP] {name} labeled \"{label}\"")
    return web.json_response({"status": "ok", "label": label})

  async def handle_backup_download(self, request):
    name = request.match_info.get("name")
    if not name:
      raise web.HTTPBadRequest(text="Missing name")
    backup_dir = os.path.join(PITSTOP_DATA_DIR, BACKUP_DIR_NAME)
    fpath = os.path.normpath(os.path.join(backup_dir, name))
    if not fpath.startswith(backup_dir + os.sep):
      raise web.HTTPBadRequest(text="Invalid backup name")
    if not os.path.isfile(fpath):
      raise web.HTTPNotFound(text=f"Backup '{name}' not found")
    return web.FileResponse(fpath, headers={
      "Content-Disposition": f'attachment; filename="{name}"',
    })

  async def handle_backup_restore(self, request):
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    name = body.get("name")
    if not name:
      raise web.HTTPBadRequest(text="Missing 'name'")
    backup_dir = os.path.join(PITSTOP_DATA_DIR, BACKUP_DIR_NAME)
    fpath = os.path.normpath(os.path.join(backup_dir, name))
    if not fpath.startswith(backup_dir + os.sep):
      raise web.HTTPBadRequest(text="Invalid backup name")
    if not os.path.isfile(fpath):
      raise web.HTTPNotFound(text=f"Backup '{name}' not found")
    with open(fpath) as f:
      data = json.load(f)
    restored = 0
    for key, val in data.get("params", {}).items():
      try:
        self.params.put(key, bytes.fromhex(val) if isinstance(val, str) and len(val) > 0 else val)
        restored += 1
      except Exception:
        logger.exception(f"Failed to restore param {key}")
    logger.info(f"[BACKUP] restored {name} ({restored} params)")
    return web.json_response({"restored": restored, "status": "ok"})

  # ---- Models ----

  @staticmethod
  def _model_file_cached(model_dir, fname):
    """Return True if fname or its chunked equivalent exists on disk."""
    return (os.path.isfile(os.path.join(model_dir, fname)) or
            os.path.isfile(os.path.join(model_dir, fname + '.chunkmanifest')))

  @staticmethod
  def _bundle_files(bundle) -> set:
    files = set()
    for m in getattr(bundle, 'models', []):
      if getattr(getattr(m, 'artifact', None), 'fileName', None):
        files.add(m.artifact.fileName)
      if getattr(getattr(m, 'metadata', None), 'fileName', None):
        files.add(m.metadata.fileName)
    return files

  async def handle_models_list(self, request):
    try:
      fetcher = ModelFetcher(self.params)
      bundles = fetcher.get_available_bundles()
      model_dir = Paths.model_root()
      result = []
      for b in bundles:
        d = b.to_dict()
        files = self._bundle_files(b)
        d['isCached'] = bool(files) and all(
          self._model_file_cached(model_dir, f) for f in files
        )
        d['cachedFiles'] = [f for f in files if self._model_file_cached(model_dir, f)]
        result.append(d)
      return web.json_response(result)
    except Exception as e:
      logger.exception("Failed to list models")
      return web.json_response({"error": str(e)}, status=500)

  async def handle_models_delete(self, request):
    name = request.match_info.get("name", "")
    if not name:
      raise web.HTTPBadRequest(text="Missing bundle name")
    try:
      fetcher = ModelFetcher(self.params)
      bundles = fetcher.get_available_bundles()
    except Exception as e:
      raise web.HTTPInternalServerError(text=str(e)) from e
    bundle = next((b for b in bundles if b.internalName == name), None)
    if bundle is None:
      raise web.HTTPNotFound(text=f"Bundle '{name}' not found")
    model_dir = Paths.model_root()
    files = self._bundle_files(bundle)
    deleted = []
    for fname in files:
      base = os.path.join(model_dir, fname)
      # Remove direct file
      if os.path.isfile(base):
        os.remove(base)
        deleted.append(fname)
      # Remove chunked files
      manifest = base + '.chunkmanifest'
      if os.path.isfile(manifest):
        try:
          num_chunks = int(open(manifest).read().strip())
        except Exception:
          num_chunks = 0
        os.remove(manifest)
        deleted.append(fname + '.chunkmanifest')
        for i in range(num_chunks):
          chunk = f"{base}.chunk{i+1:02d}of{num_chunks:02d}"
      if os.path.isfile(chunk):
        os.remove(chunk)
        deleted.append(os.path.basename(chunk))
    logger.info(f"[MODEL] deleted {name} ({len(deleted)} files)")
    return web.json_response({"status": "ok", "deleted": deleted, "bundle": name})

  async def handle_models_active(self, request):
    active = get_active_bundle(self.params)
    if active is not None:
      return web.json_response(active.to_dict())
    return web.json_response({"internalName": DEFAULT_MODEL, "displayName": DEFAULT_MODEL, "isDefault": True})

  async def handle_models_select(self, request):
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    index = body.get("index")
    if index is None:
      raise web.HTTPBadRequest(text="Missing 'index'")
    self.params.put("ModelManager_DownloadIndex", int(index))
    logger.info(f"[MODEL] selected index {index}")
    return web.json_response({"status": "ok", "index": index})

  async def handle_models_select_default(self, request):
    self.params.remove("ModelManager_ActiveBundle")
    logger.info("[MODEL] reset to default")
    return web.json_response({"status": "ok"})

  async def handle_models_progress(self, request):
    if self._model_state is None:
      return web.json_response({"error": "no model state"}, status=503)
    state = self._model_state.to_dict()
    return web.json_response({
      "selectedBundle": state.get("selectedBundle"),
      "activeBundle": state.get("activeBundle"),
      "availableBundles": state.get("availableBundles", []),
    })

  async def handle_models_cancel(self, request):
    self.params.remove("ModelManager_DownloadIndex")
    logger.info("[MODEL] download cancelled")
    return web.json_response({"status": "ok"})

  async def handle_models_refresh(self, request):
    self.params.remove("ModelManager_LastSyncTime")
    logger.info("[MODEL] refresh triggered")
    return web.json_response({"status": "ok"})

  async def handle_models_cache_clear(self, request):
    self.params.put_bool("ModelManager_ClearCache", True)
    logger.info("[MODEL] cache clear requested")
    return web.json_response({"status": "ok"})

  async def handle_models_favorites(self, request):
    if request.method == "GET":
      raw_b = self.params.get("ModelManager_Favs")
      raw = raw_b.decode("utf-8", errors="replace") if isinstance(raw_b, bytes) else ""
      refs = [r for r in raw.split(";") if r] if raw else []
      return web.json_response(refs)
    else:
      try:
        body = await request.json()
      except Exception:
        raise web.HTTPBadRequest(text="Invalid JSON") from None
      refs = body.get("refs", [])
      self.params.put("ModelManager_Favs", ";".join(refs))
      logger.info(f"[MODEL] favorites saved ({len(refs)} refs)")
      return web.json_response({"status": "ok", "count": len(refs)})

  async def handle_settings_favorites(self, request):
    fpath = os.path.join(PITSTOP_DATA_DIR, "settings_favs.json")
    if request.method == "GET":
      try:
        with open(fpath) as f:
          refs = json.load(f)
      except (FileNotFoundError, json.JSONDecodeError):
        refs = []
      return web.json_response(refs)
    else:
      try:
        body = await request.json()
      except Exception:
        raise web.HTTPBadRequest(text="Invalid JSON") from None
      refs = body.get("refs", [])
      os.makedirs(PITSTOP_DATA_DIR, exist_ok=True)
      with open(fpath, "w") as f:
        json.dump(refs, f)
      logger.info(f"[SETTINGS] favorites saved ({len(refs)} refs)")
      return web.json_response({"status": "ok", "count": len(refs)})

  # ---- System actions ----

  async def handle_update_status(self, request):
    def _getstr(key):
      try:
        v = self.params.get(key)
      except Exception:
        return ""
      return v.decode("utf-8", errors="replace").strip() if isinstance(v, bytes) else (v or "")

    update_available = self.params.get_bool("UpdateAvailable")
    current_desc = _getstr("UpdaterCurrentDescription")
    new_desc = _getstr("UpdaterNewDescription")
    fork_url = _getstr("UpdaterForkUrl")

    # Patchwork: upstream compares remote hash instead of FINALIZED vs BASEDIR,
    # so UpdateAvailable can be True even when staged FINALIZED == running BASEDIR.
    # Guard with description equality.
    available = update_available and new_desc != current_desc

    return web.json_response({"available": available, "current_description": current_desc, "description": new_desc, "fork_url": fork_url})

  async def handle_system_reboot(self, request):
    subprocess.Popen(["sudo", "reboot"])
    logger.info("[SYSTEM] reboot requested")
    return web.json_response({"status": "rebooting"})

  async def handle_system_restart(self, request):
    subprocess.Popen(["sudo", "systemctl", "restart", "comma"])
    logger.info("[SYSTEM] restart requested")
    return web.json_response({"status": "restarting"})

  # ---- CAN API (fused) ----

  async def handle_can_status(self, request):
    try:
      dbc_names = self._can_handler.dbc_names
    except Exception:
      dbc_names = None
    return web.json_response({
      "car": list(dbc_names.keys()) if dbc_names else None,
      "dbc_loaded": self._can_handler.dbc is not None,
      "api_enabled": self.params.get_bool("PitStopEnabled"),
      "offroad": self.params.get_bool("IsOffroad"),
    })

  async def handle_can_signals(self, request):
    return web.json_response(self._can_handler.get_signals())

  async def handle_can_signal_send(self, request):
    msg_name = request.match_info.get("name")
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    values = body.get("values", {})
    bus = body.get("bus", 0)
    result = self._can_handler.send_signal(msg_name, values, bus)
    if result is None:
      raise web.HTTPBadRequest(text=f"Unknown message: {msg_name}")
    logger.info(f"[CAN] signal {msg_name} ({len(values)} values)")
    return web.json_response(result)

  async def handle_can_batch_send(self, request):
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    if not isinstance(body, list):
      raise web.HTTPBadRequest(text="Expected array of messages")
    results = []
    for item in body:
      msg_name = item.get("message")
      values = item.get("values", {})
      bus = item.get("bus", 0)
      result = self._can_handler.send_signal(msg_name, values, bus)
      results.append({"message": msg_name, "ok": result is not None})
    ok = sum(1 for r in results if r["ok"])
    logger.info(f"[CAN] batch {len(results)} signals ({ok} ok)")
    return web.json_response(results)

  async def handle_can_raw_send(self, request):
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    address = body.get("address")
    data_hex = body.get("data")
    bus = body.get("bus", 0)
    if address is None or data_hex is None:
      raise web.HTTPBadRequest(text="Missing address or data")
    try:
      data = bytes.fromhex(data_hex)
    except ValueError:
      raise web.HTTPBadRequest(text="Invalid hex data") from None
    self._can_handler.send_raw(int(address), data, int(bus))
    logger.info(f"[CAN] raw 0x{int(address):X} ({len(data)} bytes) bus:{bus}")
    return web.json_response({"address": int(address), "data": data.hex(), "bus": int(bus)})

  # ---- OpenAPI / Swagger ----

  async def handle_error_log(self, request):
    crash_log = "/data/community/crashes/error.log"
    try:
      with open(crash_log) as f:
        content = f.read()
    except FileNotFoundError:
      return web.json_response({"error": "no error log"}, status=404)
    except Exception as e:
      return web.json_response({"error": f"failed to read log: {e}"}, status=500)
    return web.json_response({"path": crash_log, "content": content})

  # ---- Unified log reader ----

  def _read_swaglog(self, limit=500, min_level=0, search=None, proc=None):
    import glob
    log_dir = Paths.swaglog_root()
    pattern = os.path.join(log_dir, 'swaglog.*')
    files = sorted(glob.glob(pattern), reverse=True)
    entries = []
    search_lc = search.lower() if search else None
    proc_lc   = proc.lower()   if proc   else None
    for fpath in files[:15]:
      try:
        with open(fpath, 'r', errors='replace') as f:
          for line in f:
            line = line.strip()
            if not line:
              continue
            try:
              d = json.loads(line)
              levelnum = d.get('levelnum', 20)
              if levelnum < min_level:
                continue
              name = d.get('name', '')
              # swaglog uses msg$s for plain strings, msg for structured dicts
              raw_msg = d.get('msg$s') or d.get('msg', '')
              msg = json.dumps(raw_msg) if isinstance(raw_msg, (dict, list)) else str(raw_msg)
              if proc_lc and proc_lc not in name.lower():
                continue
              if search_lc and search_lc not in msg.lower() and search_lc not in name.lower():
                continue
              if levelnum >= 50: lvlname = 'CRITICAL'
              elif levelnum >= 40: lvlname = 'ERROR'
              elif levelnum >= 30: lvlname = 'WARNING'
              elif levelnum >= 10: lvlname = 'DEBUG' if levelnum < 20 else 'INFO'
              else: lvlname = 'DEBUG'
              entries.append({
                'ts':       d.get('created', 0),
                'level':    (d.get('levelname') or lvlname).upper(),
                'levelnum': levelnum,
                'source':   'swaglog',
                'process':  name,
                'filename': d.get('filename', ''),
                'lineno':   d.get('lineno', 0),
                'msg':      msg,
              })
            except Exception:
              pass
      except Exception:
        continue
      if len(entries) >= limit * 3:
        break
    entries.sort(key=lambda x: x['ts'], reverse=True)
    return entries[:limit]

  def _read_journal(self, limit=500, search=None, proc=None, kernel=False):
    cmd = ['journalctl', '-o', 'json', f'-n{limit}', '--no-pager']
    if kernel:
      cmd.append('-k')
    if proc:
      cmd += ['-t', proc]
    try:
      result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
      PRIO_MAP = {0:'CRITICAL',1:'CRITICAL',2:'CRITICAL',3:'ERROR',4:'WARNING',5:'INFO',6:'INFO',7:'DEBUG'}
      PRIO_NUM = {0:50,1:50,2:50,3:40,4:30,5:20,6:20,7:10}
      search_lc = search.lower() if search else None
      entries = []
      for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
          continue
        try:
          d = json.loads(line)
          raw_msg = d.get('MESSAGE', '')
          if isinstance(raw_msg, list):
            msg = ''.join(chr(c) for c in raw_msg if isinstance(c, int) and c < 128)
          else:
            msg = str(raw_msg)
          if search_lc and search_lc not in msg.lower():
            continue
          prio = int(d.get('PRIORITY', 6))
          ts_us = d.get('__REALTIME_TIMESTAMP', '0')
          ts = int(ts_us) / 1_000_000 if ts_us else 0
          identifier = d.get('SYSLOG_IDENTIFIER') or d.get('_COMM', '') or ''
          unit = d.get('_SYSTEMD_UNIT', '')
          process = identifier or unit
          entries.append({
            'ts':       ts,
            'level':    PRIO_MAP.get(prio, 'INFO'),
            'levelnum': PRIO_NUM.get(prio, 20),
            'source':   'kernel' if kernel else 'journal',
            'process':  process,
            'filename': unit,
            'lineno':   0,
            'msg':      msg,
          })
        except Exception:
          pass
      entries.reverse()  # journalctl returns oldest-first with -n
      return entries
    except Exception as e:
      logger.warning(f"journalctl failed: {e}")
      return []

  def _read_crashes(self, limit=30, search=None):
    crash_dir = Paths.crash_log_root()
    entries = []
    search_lc = search.lower() if search else None
    try:
      files = [f for f in os.listdir(crash_dir)
               if f.endswith('.log') and f != 'error.log']
      files.sort(reverse=True)
      for fname in files[:limit]:
        fpath = os.path.join(crash_dir, fname)
        try:
          stat = os.stat(fpath)
          with open(fpath, 'r', errors='replace') as f:
            content = f.read(32768)
          if search_lc and search_lc not in content.lower():
            continue
          entries.append({
            'ts':       stat.st_mtime,
            'level':    'ERROR',
            'levelnum': 40,
            'source':   'crash',
            'process':  'crash',
            'filename': fname,
            'lineno':   0,
            'msg':      content,
          })
        except Exception:
          pass
    except Exception:
      pass
    return entries

  def _read_pitstop(self, limit=500, min_level=0, search=None):
    fpath = "/tmp/pitstop.log"
    entries = []
    search_lc = search.lower() if search else None
    LVL_MAP = {'CRITICAL': 50, 'ERROR': 40, 'WARNING': 30, 'INFO': 20, 'DEBUG': 10}
    try:
      with open(fpath, 'r', errors='replace') as f:
        for line in f:
          line = line.rstrip('\n\r')
          if not line:
            continue
          # Parse "LEVEL:name:message" or "LEVEL:name:..."
          lvl = 'INFO'
          name = ''
          msg = line
          for possible_lvl in ('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'):
            if line.startswith(possible_lvl + ':'):
              lvl = possible_lvl
              rest = line[len(lvl)+1:]
              colon = rest.find(':')
              if colon > 0:
                name = rest[:colon]
                msg = rest[colon+1:]
              else:
                msg = rest
              break
          levelnum = LVL_MAP.get(lvl, 20)
          if levelnum < min_level:
            continue
          if search_lc and search_lc not in msg.lower() and search_lc not in name.lower():
            continue
          entries.append({
            'ts':       os.path.getmtime(fpath),
            'level':    lvl,
            'levelnum': levelnum,
            'source':   'pitstop',
            'process':  name,
            'filename': 'pitstop.log',
            'lineno':   0,
            'msg':      msg,
          })
    except FileNotFoundError:
      return []
    except Exception as e:
      logger.warning(f"Failed to read pitstop log: {e}")
      return []
    entries.reverse()
    return entries[:limit]

  async def handle_logs(self, request):
    source  = request.rel_url.query.get('source', 'swaglog')
    search  = request.rel_url.query.get('search', '').strip() or None
    proc    = request.rel_url.query.get('process', '').strip() or None
    try:
      limit     = min(int(request.rel_url.query.get('limit', '500')), 2000)
      min_level = int(request.rel_url.query.get('level', '0'))
    except (ValueError, TypeError):
      limit, min_level = 500, 0
    try:
      if source == 'journal':
        entries = self._read_journal(limit=limit, search=search, proc=proc)
      elif source == 'kernel':
        entries = self._read_journal(limit=limit, search=search, kernel=True)
      elif source == 'crash':
        entries = self._read_crashes(limit=50, search=search)
      elif source == 'pitstop':
        entries = self._read_pitstop(limit=limit, min_level=min_level, search=search)
      else:
        entries = self._read_swaglog(limit=limit, min_level=min_level, search=search, proc=proc)
      return web.json_response(entries)
    except Exception as e:
      logger.exception("Failed to read logs")
      return web.json_response({"error": str(e)}, status=500)

  async def handle_openapi(self, request):
    host = request.host.split(":")[0] if ":" in request.host else request.host
    schema = generate_openapi_schema(host=host, port=EXTERNAL_PORT, dbc=self._can_handler.dbc)
    return web.json_response(schema)

  async def handle_docs(self, request):
    return web.Response(text=SWAGGER_HTML, content_type="text/html")

  # ---- Static SPA (must be last) ----

  async def handle_static(self, request):
    filename = request.match_info.get("filename", "index.html")
    filepath = os.path.normpath(os.path.join(STATIC_DIR, filename))
    if not filepath.startswith(STATIC_DIR):
      raise web.HTTPForbidden()
    if os.path.isfile(filepath):
      return web.FileResponse(filepath)
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
      return web.FileResponse(index_path)
    raise web.HTTPNotFound()

  def build_app(self):
    app = web.Application()
    app.middlewares.append(access_log_middleware)

    # System
    app.router.add_get("/api/status", self.handle_status)
    app.router.add_get("/api/device", self.handle_device)
    app.router.add_get("/api/telemetry", self.handle_telemetry)
    app.router.add_get("/api/diag", self.handle_diag)

    # New endpoints
    app.router.add_get("/api/gps", self.handle_gps)
    app.router.add_get("/api/calibration", self.handle_calibration)
    app.router.add_get("/api/network", self.handle_network)
    app.router.add_get("/api/sunnylink", self.handle_sunnylink)
    app.router.add_get("/api/storage", self.handle_storage)
    app.router.add_get("/api/speeds", self.handle_speeds)

    # Params
    app.router.add_get("/api/params", self.handle_params_list)
    app.router.add_get("/api/params/{key}", self.handle_param_get)
    app.router.add_post("/api/params/{key}", self.handle_param_set)
    app.router.add_put("/api/params/{key}/bool", self.handle_param_put_bool)
    app.router.add_put("/api/params/{key}/int", self.handle_param_put_int)
    app.router.add_put("/api/params/{key}/float", self.handle_param_put_float)

    # Settings
    app.router.add_get("/api/settings/schema", self.handle_settings_schema)
    app.router.add_get("/api/capabilities", self.handle_capabilities)

    # Backup
    app.router.add_get("/api/backup", self.handle_backup_list)
    app.router.add_post("/api/backup/create", self.handle_backup_create)
    app.router.add_post("/api/backup/restore", self.handle_backup_restore)
    app.router.add_delete("/api/backup/{name}", self.handle_backup_delete)
    app.router.add_post("/api/backup/{name}/label", self.handle_backup_set_label)
    app.router.add_get("/api/backup/download/{name}", self.handle_backup_download)
    app.router.add_post("/api/backup/upload", self.handle_backup_upload)

    # Models
    app.router.add_get("/api/models", self.handle_models_list)
    app.router.add_get("/api/models/active", self.handle_models_active)
    app.router.add_post("/api/models/select", self.handle_models_select)
    app.router.add_post("/api/models/select/default", self.handle_models_select_default)
    app.router.add_get("/api/models/progress", self.handle_models_progress)
    app.router.add_post("/api/models/cancel", self.handle_models_cancel)
    app.router.add_post("/api/models/refresh", self.handle_models_refresh)
    app.router.add_delete("/api/models/cache", self.handle_models_cache_clear)
    app.router.add_get("/api/models/favorites", self.handle_models_favorites)
    app.router.add_post("/api/models/favorites", self.handle_models_favorites)
    app.router.add_delete("/api/models/{name}", self.handle_models_delete)

    # Settings favorites
    app.router.add_get("/api/settings/favorites", self.handle_settings_favorites)
    app.router.add_post("/api/settings/favorites", self.handle_settings_favorites)

    # System actions
    app.router.add_get("/api/update", self.handle_update_status)
    app.router.add_post("/api/system/reboot", self.handle_system_reboot)
    app.router.add_post("/api/system/restart", self.handle_system_restart)

    # CAN API (fused)
    app.router.add_get("/api/v1/status", self.handle_can_status)
    app.router.add_get("/api/v1/signals", self.handle_can_signals)
    app.router.add_post("/api/v1/signals/{name}", self.handle_can_signal_send)
    app.router.add_post("/api/v1/signals/batch", self.handle_can_batch_send)
    app.router.add_post("/api/v1/can/send", self.handle_can_raw_send)

    # Logs
    app.router.add_get("/api/logs/errors", self.handle_error_log)
    app.router.add_get("/api/logs", self.handle_logs)

    # OpenAPI / Swagger
    app.router.add_get("/openapi.json", self.handle_openapi)
    app.router.add_get("/docs", self.handle_docs)

    # SPA catch-all (must be last)
    app.router.add_get("/{filename:.*}", self.handle_static)

    return app


def _setup_port_redirect():
  import subprocess
  ipt = ["sudo", "iptables-legacy", "-t", "nat"]
  rule = ["-p", "tcp", "--dport", str(EXTERNAL_PORT), "-j", "REDIRECT", "--to-port", str(PORT)]
  subprocess.run(ipt + ["-D", "PREROUTING"] + rule, capture_output=True)
  subprocess.run(ipt + ["-A", "PREROUTING"] + rule, capture_output=True)
  subprocess.run(ipt + ["-D", "OUTPUT", "-o", "lo"] + rule, capture_output=True)
  subprocess.run(ipt + ["-A", "OUTPUT", "-o", "lo"] + rule, capture_output=True)


def main():
  logger.setLevel(logging.INFO)
  handler = logging.FileHandler("/tmp/pitstop.log")
  handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
  logger.addHandler(handler)

  _setup_port_redirect()
  server = PitStopServer()
  app = server.build_app()
  logger.info(f"PitStop starting on {HOST}:{PORT} (accessible at :{EXTERNAL_PORT})")
  web.run_app(app, host=HOST, port=PORT, print=lambda *a: None)


if __name__ == "__main__":
  raise SystemExit(
    "ERROR: pitstop.server must not be started directly.\n"
    "It is managed by the system manager (manager.py).\n"
    "For manual testing use: /usr/local/venv/bin/python3 -m pitstop.server"
  )
