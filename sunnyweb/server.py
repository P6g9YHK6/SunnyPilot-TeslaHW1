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

from cereal import messaging, custom

logger = logging.getLogger("sunnyweb")

HOST = "0.0.0.0"
PORT = 8800

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
PARAMS_METADATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sunnypilot", "sunnylink", "params_metadata.json")
BACKUP_DIR_NAME = "sunnyweb_backups"


class SunnyWebServer:
  def __init__(self):
    self.params = Params()
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

  async def handle_status(self, request):
    return web.json_response({
      "enabled": self.params.get_bool("SunnyWebEnabled"),
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

  async def handle_settings_schema(self, request):
    try:
      schema = generate_schema()
    except FileNotFoundError:
      raise web.HTTPNotFound(text="settings_ui.json not found") from None
    return web.json_response(schema)

  async def handle_capabilities(self, request):
    caps = generate_capabilities(self.params)
    return web.json_response(caps)

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
      json.dump({"created": time.monotonic(), "params": config}, f)
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
    if not fpath.startswith(backup_dir):
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

  # ---- Model downloader endpoints ----

  async def handle_models_list(self, request):
    try:
      fetcher = ModelFetcher(self.params)
      bundles = fetcher.get_available_bundles()
      raw = []
      for b in bundles:
        raw.append(b.to_dict())
      return web.json_response(raw)
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
    selected = state.get("selectedBundle")
    active = state.get("activeBundle")
    available = state.get("availableBundles", [])
    return web.json_response({
      "selectedBundle": selected,
      "activeBundle": active,
      "availableBundles": available,
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

    app.router.add_get("/api/status", self.handle_status)
    app.router.add_get("/api/device", self.handle_device)
    app.router.add_get("/api/params", self.handle_params_list)
    app.router.add_get("/api/params/{key}", self.handle_param_get)
    app.router.add_post("/api/params/{key}", self.handle_param_set)
    app.router.add_put("/api/params/{key}/bool", self.handle_param_put_bool)
    app.router.add_put("/api/params/{key}/int", self.handle_param_put_int)
    app.router.add_put("/api/params/{key}/float", self.handle_param_put_float)
    app.router.add_get("/api/settings/schema", self.handle_settings_schema)
    app.router.add_get("/api/capabilities", self.handle_capabilities)
    app.router.add_get("/api/backup", self.handle_backup_list)
    app.router.add_post("/api/backup/create", self.handle_backup_create)
    app.router.add_post("/api/backup/restore", self.handle_backup_restore)

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

    app.router.add_get("/{filename:.*}", self.handle_static)

    return app


def main():
  logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
  logger.setLevel(logging.INFO)

  server = SunnyWebServer()
  app = server.build_app()
  logger.info(f"SunnyWeb starting on {HOST}:{PORT}")
  web.run_app(app, host=HOST, port=PORT, print=lambda *a: None)


if __name__ == "__main__":
  main()
