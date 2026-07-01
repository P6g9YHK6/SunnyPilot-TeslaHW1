import json
import logging
import os
import threading
import time

from aiohttp import web

from openpilot.common.params import Params, ParamKeyType
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
PORT = 80

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
    self._model_thread = threading.Thread(target=self._model_manager_loop, daemon=True)
    self._model_thread.start()

  def _model_manager_loop(self):
    try:
      sock = messaging.sub_sock('modelManagerSP', conflate=True, timeout=1000)
      while self._running:
        msg = messaging.recv_one_or_none(sock)
        if msg is not None:
          self._model_state = msg.modelManagerSP
    except Exception:
      logger.warning("modelManagerSP subscriber not available (no cereal context)")

  # ---- System ----

  async def handle_status(self, request):
    return web.json_response({
      "enabled": self.params.get_bool("PitStopEnabled"),
      "is_offroad": self.params.get_bool("IsOffroad"),
      "is_metric": self.params.get_bool("IsMetric"),
      "version": 1,
    })

  async def handle_device(self, request):
    dongle_id = self.params.get("DongleId", encoding="utf-8")
    hardware_serial = self.params.get("HardwareSerial", encoding="utf-8")
    try:
      build = get_build_metadata()
      version = build.openpilot.version
      branch = build.channel
      git_commit = build.openpilot.git_commit
      git_commit_date = build.openpilot.git_commit_date
      is_dirty = build.openpilot.is_dirty
    except Exception:
      version = self.params.get("Version", encoding="utf-8")
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
      with open(PARAMS_METADATA_PATH) as f:
        metadata = json.load(f)
    except Exception:
      metadata = {}
    return web.json_response(metadata)

  async def handle_param_get(self, request):
    key = request.match_info.get("key")
    raw = self.params.get(key)
    if raw is None:
      raise web.HTTPNotFound(text=f"Param '{key}' not found")
    param_type = self.params.get_param_type(key)
    return web.json_response({
      "key": key,
      "value": raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw),
      "type": str(param_type),
    })

  async def handle_param_set(self, request):
    key = request.match_info.get("key")
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    value = body.get("value")
    if value is None:
      raise web.HTTPBadRequest(text="Missing 'value'")
    self.params.put(key, str(value))
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
    self.params.put_bool(key, value)
    return web.json_response({"key": key, "value": value, "status": "ok"})

  async def handle_param_put_int(self, request):
    key = request.match_info.get("key")
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    value = body.get("value")
    if not isinstance(value, int):
      raise web.HTTPBadRequest(text="'value' must be integer")
    self.params.put_int(key, value)
    return web.json_response({"key": key, "value": value, "status": "ok"})

  async def handle_param_put_float(self, request):
    key = request.match_info.get("key")
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    value = body.get("value")
    if not isinstance(value, (int, float)):
      raise web.HTTPBadRequest(text="'value' must be a number")
    self.params.put_float(key, float(value))
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
    for k in self.params.all_keys(ParamKeyType.PERSISTENT):
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

  async def handle_models_list(self, request):
    try:
      fetcher = ModelFetcher(self.params)
      bundles = fetcher.get_available_bundles()
      return web.json_response([b.to_dict() for b in bundles])
    except Exception as e:
      logger.exception("Failed to list models")
      return web.json_response({"error": str(e)}, status=500)

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
    self.params.put("ModelManager_DownloadIndex", str(index))
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
      raw = self.params.get("ModelManager_Favs", encoding="utf-8") or ""
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

  async def handle_openapi(self, request):
    host = request.host.split(":")[0] if ":" in request.host else request.host
    port = int(request.host.split(":")[1]) if ":" in request.host else PORT
    schema = generate_openapi_schema(host=host, port=port, dbc=self._can_handler.dbc)
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

    # CAN API (fused)
    app.router.add_get("/api/v1/status", self.handle_can_status)
    app.router.add_get("/api/v1/signals", self.handle_can_signals)
    app.router.add_post("/api/v1/signals/{name}", self.handle_can_signal_send)
    app.router.add_post("/api/v1/signals/batch", self.handle_can_batch_send)
    app.router.add_post("/api/v1/can/send", self.handle_can_raw_send)

    # OpenAPI / Swagger
    app.router.add_get("/openapi.json", self.handle_openapi)
    app.router.add_get("/docs", self.handle_docs)

    # SPA catch-all (must be last)
    app.router.add_get("/{filename:.*}", self.handle_static)

    return app


def main():
  logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
  logger.setLevel(logging.INFO)

  server = PitStopServer()
  app = server.build_app()
  logger.info(f"PitStop starting on {HOST}:{PORT}")
  web.run_app(app, host=HOST, port=PORT, print=lambda *a: None)


if __name__ == "__main__":
  main()
