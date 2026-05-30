import json
import logging
import os

from aiohttp import web

from openpilot.common.params import Params, ParamKeyType
from openpilot.system.hardware.hw import Paths
from openpilot.system.version import get_build_metadata
from openpilot.sunnypilot.sunnylink.capabilities import generate_capabilities

logger = logging.getLogger("sunnyweb")

HOST = "0.0.0.0"
PORT = 8800

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
SETTINGS_UI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sunnypilot", "sunnylink", "settings_ui.json")
PARAMS_METADATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sunnypilot", "sunnylink", "params_metadata.json")


class SunnyWebServer:
  def __init__(self):
    self.params = Params()

  async def handle_status(self, request):
    enabled = self.params.get_bool("SunnyWebEnabled")
    return web.json_response({
      "enabled": enabled,
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
      with open(SETTINGS_UI_PATH) as f:
        schema = json.load(f)
    except FileNotFoundError:
      raise web.HTTPNotFound(text="settings_ui.json not found") from None
    return web.json_response(schema)

  async def handle_capabilities(self, request):
    caps = generate_capabilities(self.params)
    return web.json_response(caps)

  async def handle_backup_list(self, request):
    backup_dir = os.path.join(Paths.comma_home(), "sunnyweb_backups")
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
    import time
    backup_dir = os.path.join(Paths.comma_home(), "sunnyweb_backups")
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
    backup_dir = os.path.join(Paths.comma_home(), "sunnyweb_backups")
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

    app.router.add_get("/{filename:.*}", self.handle_static)

    return app


def main():
  logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
  logger.setLevel(logging.INFO)

  server = SunnyWebServer()
  app = server.build_app()
  logger.info(f"SunnyWeb starting on {HOST}:{PORT}")
  web.run_app(app, host=HOST, port=PORT)


if __name__ == "__main__":
  main()
