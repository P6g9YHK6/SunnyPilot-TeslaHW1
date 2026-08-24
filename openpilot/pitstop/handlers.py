import json
import logging
import os
import subprocess
import threading
import time

from aiohttp import web

from openpilot.common.params import Params, ParamKeyFlag
from openpilot.system.version import get_build_metadata
from openpilot.sunnypilot.sunnylink.capabilities import generate_capabilities
from openpilot.sunnypilot.sunnylink.tools.generate_settings_schema import generate_schema
from openpilot.pitstop.schema import generate_openapi_schema

from .constants import STATIC_DIR, PITSTOP_DATA_DIR, BACKUP_DIR_NAME, EXTERNAL_PORT

logger = logging.getLogger("pitstop")

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


class HandlerMixin:

  async def handle_diag(self, request):
    if self._diag is None:
      return web.json_response({"error": "no diag data"}, status=503)
    return web.json_response(self._diag)

  async def handle_gps(self, request):
    g = self._gps_location
    if g is None:
      return web.json_response({"error": "no gps fix"}, status=503)
    return web.json_response({
      "latitude": g.latitude, "longitude": g.longitude, "altitude": g.altitude,
      "speed": g.speed, "bearing": g.bearingDeg, "accuracy": g.horizontalAccuracy,
      "vertical_accuracy": g.verticalAccuracy, "bearing_accuracy": g.bearingAccuracyDeg,
      "speed_accuracy": g.speedAccuracy, "has_fix": g.hasFix,
      "satellites": g.satelliteCount, "source": str(g.source).split('.')[-1],
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
      "enabled": enabled, "registered": registered, "dongle_id": dongle_id,
      "online": online, "temp_fault": temp_fault,
      "ready": enabled and registered and not temp_fault,
    })

  async def handle_storage(self, request):
    def _usage(path):
      try:
        s = os.statvfs(path)
        total = s.f_frsize * s.f_blocks
        free = s.f_frsize * s.f_bfree
        used = total - free
        return {"total": total, "used": used, "free": free,
                "pct": round(used / total * 100, 1) if total else 0}
      except Exception:
        return None
    return web.json_response({
      "root": _usage("/"), "data": _usage("/data") if os.path.isdir("/data") else None,
      "logs": _usage(Paths.log_root()), "models": _usage(Paths.model_root()),
      "crashes": _usage(Paths.crash_log_root()),
    })

  async def handle_speeds(self, request):
    if self._speed_data is None:
      return web.json_response({"error": "no speed data"}, status=503)
    return web.json_response(self._speed_data)

  async def handle_cockpit(self, request):
    if self._cockpit_data is None:
      return web.json_response({"error": "no cockpit data"}, status=503)
    return web.json_response(self._cockpit_data)

  async def handle_telemetry(self, request):
    ds = self._device_state
    cs = None
    cp = None
    try:
      gear = str(cs.gearShifter) if cs is not None else None
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
        "speed_ms": float(cs.vEgo) if cs is not None else None, "gear": gear,
        "standstill": bool(cs.standstill) if cs is not None else None,
      },
      "device": {
        "temp_c": float(ds.maxTempC) if ds is not None else None,
        "memory_pct": float(ds.memoryUsagePercent) if ds is not None else None,
        "cpu_pct": float(ds.cpuUsagePercent[0]) if ds is not None and len(ds.cpuUsagePercent) > 0 else None,
        "free_space_pct": float(ds.freeSpacePercent) if ds is not None else None,
        "network_type": net_type, "thermal_status": thermal,
      },
    })

  async def handle_status(self, request):
    return web.json_response({
      "enabled": self.params.get_bool("PitStopEnabled"),
      "is_offroad": self.params.get_bool("IsOffroad"),
      "is_metric": self.params.get_bool("IsMetric"),
      "engaged": self._is_engaged, "version": 1,
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
      "dongle_id": dongle_id, "hardware_serial": hardware_serial,
      "version": version, "branch": branch, "git_commit": git_commit,
      "git_commit_date": git_commit_date, "git_repo": git_repo,
      "is_dirty": is_dirty,
    })

  async def handle_params_list(self, request):
    try:
      keys = sorted(k.decode("utf-8") for k in self.params.all_keys())
      return web.json_response({k: {} for k in keys})
    except Exception as e:
      logger.exception("failed to list params")
      return web.json_response({"error": f"failed to list params: {e}"}, status=500)

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
    return web.json_response({"key": key, "value": float(value), "status": "ok"})

  async def handle_settings_schema(self, request):
    try:
      schema = generate_schema()
    except FileNotFoundError:
      raise web.HTTPNotFound(text="settings_ui.json not found") from None
    except (json.JSONDecodeError, ValueError) as e:
      raise web.HTTPInternalServerError(text=f"settings_ui.json is corrupted: {e}") from None
    return web.json_response(schema)

  async def handle_capabilities(self, request):
    caps = generate_capabilities(self.params)
    return web.json_response(caps)

  async def handle_backup_list(self, request):
    backup_dir = os.path.join(PITSTOP_DATA_DIR, BACKUP_DIR_NAME)
    backups = []
    if os.path.isdir(backup_dir):
      for fname in sorted(os.listdir(backup_dir)):
        fpath = os.path.join(backup_dir, fname)
        if os.path.isfile(fpath):
          info = {"name": fname, "size": os.path.getsize(fpath), "mtime": os.path.getmtime(fpath)}
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

  async def handle_update_status(self, request):
    def _getstr(key):
      try:
        v = self.params.get(key)
      except Exception:
        return ""
      return v.decode("utf-8", errors="replace").strip() if isinstance(v, bytes) else (v or "")

    updater_state = _getstr("UpdaterState") or "idle"
    update_available = self.params.get_bool("UpdateAvailable")
    fetch_available = self.params.get_bool("UpdaterFetchAvailable")
    failed_count = self.params.get("UpdateFailedCount", return_default=True) or 0
    current_desc = _getstr("UpdaterCurrentDescription")
    new_desc = _getstr("UpdaterNewDescription")
    fork_url = _getstr("UpdaterForkUrl")
    last_exception = _getstr("LastUpdateException")
    try:
      last_update_dt = self.params.get("LastUpdateTime")
      last_update_time = last_update_dt.isoformat() if last_update_dt else ""
    except Exception:
      last_update_time = ""

    progress_states = {"checking...": "checking", "downloading...": "downloading", "finalizing update...": "finalizing"}
    if updater_state in progress_states:
      state = progress_states[updater_state]
    elif update_available:
      state = "ready"
    elif failed_count > 0:
      state = "failed"
    elif fetch_available:
      state = "fetch_available"
    else:
      state = "up_to_date"

    return web.json_response({
      "state": state,
      "available": update_available and new_desc != current_desc,  # kept for compat
      "current_description": current_desc,
      "description": new_desc,
      "fork_url": fork_url,
      "failed_count": failed_count,
      "last_update_time": last_update_time,
      "last_exception": last_exception if state == "failed" else "",
    })

  async def handle_update_check(self, request):
    result = subprocess.run(["pkill", "-SIGUSR1", "-f", "system.updated.updated"], check=False)
    found = result.returncode == 0
    logger.info(f"[UPDATE] check requested via PitStop (updated running: {found})")
    if not found:
      raise web.HTTPServiceUnavailable(text="updated is not running")
    return web.json_response({"status": "checking"})

  async def handle_system_reboot(self, request):
    Params().put_bool("DoReboot", True)
    logger.info("[SYSTEM] clean reboot requested via PitStop")
    return web.json_response({"status": "rebooting"})

  async def handle_system_restart(self, request):
    Params().put_bool("OnroadCycleRequested", True)
    logger.info("[SYSTEM] onroad cycle requested via PitStop")
    return web.json_response({"status": "restarting"})

  async def handle_pitstop_restart(self, request):
    logger.info("[SYSTEM] PitStop restart requested")
    threading.Thread(target=lambda: (time.sleep(0.5), os._exit(0))).start()
    return web.json_response({"status": "restarting"})

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
    return web.json_response({"address": int(address), "data": data.hex(), "bus": int(bus)})

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

  async def handle_logs(self, request):
    source = request.rel_url.query.get('source', 'swaglog')
    search = request.rel_url.query.get('search', '').strip() or None
    proc = request.rel_url.query.get('process', '').strip() or None
    try:
      limit = min(int(request.rel_url.query.get('limit', '500')), 2000)
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
