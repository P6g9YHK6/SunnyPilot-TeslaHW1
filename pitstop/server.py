import json
import logging
import os
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
BACKUP_DIR_NAME = "pitstop_backups"

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


class PitStopServer:
  def __init__(self):
    self.params = Params()
    self._can_handler = CanApiHandler()
    self._running = True
    self._model_state = None
    self._car_state = None
    self._car_params = None
    self._device_state = None
    for target in (
      self._model_manager_loop,
      self._car_params_loop,
      self._device_state_loop,
    ):
      threading.Thread(target=target, daemon=True).start()

  def _subscriber_loop(self, topic, attr, field):
    try:
      sock = messaging.sub_sock(topic, conflate=True, timeout=1000)
      while self._running:
        msg = messaging.recv_one(sock)   # blocks up to 1s — zero CPU when idle
        if msg is not None:
          setattr(self, attr, getattr(msg, field))
    except Exception:
      logger.warning(f"{topic} subscriber not available")

  def _model_manager_loop(self):
    self._subscriber_loop('modelManagerSP', '_model_state', 'modelManagerSP')

  def _car_state_loop(self):
    self._subscriber_loop('carState', '_car_state', 'carState')

  def _car_params_loop(self):
    self._subscriber_loop('carParams', '_car_params', 'carParams')

  def _device_state_loop(self):
    self._subscriber_loop('deviceState', '_device_state', 'deviceState')

  # ---- System ----

  async def handle_telemetry(self, request):
    cs = self._car_state
    cp = self._car_params
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
      "version": 1,
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
      git_commit_date = build.openpilot.git_commit_date
      is_dirty = build.openpilot.is_dirty
    except Exception:
      version = _getstr("Version")
      branch = None
      git_commit = None
      git_commit_date = None
      is_dirty = None

    return web.json_response({
      "dongle_id": dongle_id,
      "hardware_serial": hardware_serial,
      "version": version,
      "branch": branch,
      "git_commit": git_commit,
      "git_commit_date": git_commit_date,
      "is_dirty": is_dirty,
    })

  # ---- Params ----

  async def handle_params_list(self, request):
    try:
      keys = sorted(k.decode("utf-8") for k in self.params.all_keys())
      return web.json_response({k: {} for k in keys})
    except Exception:
      return web.json_response({})

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
    elif isinstance(current, int):
      self.params.put(key, int(sv))
    elif isinstance(current, float):
      self.params.put(key, float(sv))
    elif isinstance(current, (dict, list)):
      self.params.put(key, json.loads(sv))
    elif isinstance(current, bytes):
      self.params.put(key, sv.encode("utf-8"))
    else:
      self.params.put(key, sv)

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
    backup_dir = os.path.join(Paths.comma_home(), BACKUP_DIR_NAME)
    backups = []
    if os.path.isdir(backup_dir):
      for fname in sorted(os.listdir(backup_dir)):
        fpath = os.path.join(backup_dir, fname)
        if os.path.isfile(fpath):
          backups.append({
            "name": fname,
            "size": os.path.getsize(fpath),
            "mtime": os.path.getmtime(fpath),
          })
    return web.json_response(backups)

  async def handle_backup_create(self, request):
    backup_dir = os.path.join(Paths.comma_home(), BACKUP_DIR_NAME)
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
    return web.json_response({"name": fname, "status": "created"})

  async def handle_backup_delete(self, request):
    name = request.match_info.get("name")
    if not name:
      raise web.HTTPBadRequest(text="Missing name")
    backup_dir = os.path.join(Paths.comma_home(), BACKUP_DIR_NAME)
    fpath = os.path.normpath(os.path.join(backup_dir, name))
    if not fpath.startswith(backup_dir + os.sep):
      raise web.HTTPBadRequest(text="Invalid backup name")
    if not os.path.isfile(fpath):
      raise web.HTTPNotFound(text=f"Backup '{name}' not found")
    os.remove(fpath)
    return web.json_response({"status": "deleted"})

  async def handle_backup_restore(self, request):
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    name = body.get("name")
    if not name:
      raise web.HTTPBadRequest(text="Missing 'name'")
    backup_dir = os.path.join(Paths.comma_home(), BACKUP_DIR_NAME)
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
    return web.json_response({"status": "ok", "index": index})

  async def handle_models_select_default(self, request):
    self.params.remove("ModelManager_ActiveBundle")
    return web.json_response({"status": "ok"})

  async def handle_models_progress(self, request):
    if self._model_state is None:
      return web.json_response({"status": "no_data"})
    state = self._model_state.to_dict()
    return web.json_response({
      "selectedBundle": state.get("selectedBundle"),
      "activeBundle": state.get("activeBundle"),
      "availableBundles": state.get("availableBundles", []),
    })

  async def handle_models_cancel(self, request):
    self.params.remove("ModelManager_DownloadIndex")
    return web.json_response({"status": "ok"})

  async def handle_models_refresh(self, request):
    self.params.remove("ModelManager_LastSyncTime")
    return web.json_response({"status": "ok"})

  async def handle_models_cache_clear(self, request):
    self.params.put_bool("ModelManager_ClearCache", True)
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
      return web.json_response({"status": "ok", "count": len(refs)})

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

  # ---- OpenAPI / Swagger ----

  async def handle_error_log(self, request):
    crash_log = "/data/community/crashes/error.log"
    try:
      with open(crash_log) as f:
        content = f.read()
    except FileNotFoundError:
      content = ""
    except Exception as e:
      content = f"Error reading log: {e}"
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
    import subprocess
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

    # System
    app.router.add_get("/api/status", self.handle_status)
    app.router.add_get("/api/device", self.handle_device)
    app.router.add_get("/api/telemetry", self.handle_telemetry)

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
  logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
  logger.setLevel(logging.INFO)

  _setup_port_redirect()
  server = PitStopServer()
  app = server.build_app()
  logger.info(f"PitStop starting on {HOST}:{PORT} (accessible at :{EXTERNAL_PORT})")
  web.run_app(app, host=HOST, port=PORT, print=lambda *a: None)


if __name__ == "__main__":
  main()
