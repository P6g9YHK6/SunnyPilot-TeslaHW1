import logging
import os
import time
import threading
import subprocess

from aiohttp import web

from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.can_api.handler import CanApiHandler

from .handlers import HandlerMixin
from .subscribers import SubscriberMixin
from .models import ModelMixin
from .osm import OsmMixin
from .diagnostics import DiagnosticMixin
from .logs import LogMixin
from .utils import UtilMixin
from .constants import HOST, PORT, EXTERNAL_PORT, PITSTOP_DATA_DIR

logger = logging.getLogger("pitstop")


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


class PitStopServer(HandlerMixin, SubscriberMixin, ModelMixin, OsmMixin, DiagnosticMixin, LogMixin, UtilMixin):

  def __init__(self):
    self.params = Params()
    self._can_handler = CanApiHandler()
    self._running = True
    self._model_state = None
    self._device_state = None
    self._diag = None
    self._gps_location = None
    self._calibration = None
    self._speed_data = {}
    self._cockpit_data = {}
    self._is_engaged = False
    self._static_version = self._hash_static()
    if not os.path.isdir(PITSTOP_DATA_DIR):
      raise SystemExit(f"ERROR: {PITSTOP_DATA_DIR} does not exist")
    try:
      test_file = os.path.join(PITSTOP_DATA_DIR, ".write_test")
      with open(test_file, "w") as f:
        f.write("test")
      os.remove(test_file)
    except Exception as e:
      raise SystemExit(f"ERROR: {PITSTOP_DATA_DIR} is not writable: {e}")
    for target in (
      self._model_manager_loop,
      self._device_state_loop,
      self._diag_loop,
      self._gps_location_loop,
    ):
      threading.Thread(target=target, daemon=True).start()

  def build_app(self):
    app = web.Application()
    app.middlewares.append(access_log_middleware)

    # System
    app.router.add_get("/api/status", self.handle_status)
    app.router.add_get("/api/device", self.handle_device)
    app.router.add_get("/api/telemetry", self.handle_telemetry)
    app.router.add_get("/api/diag", self.handle_diag)

    # Telemetry / GPS / Storage
    app.router.add_get("/api/gps", self.handle_gps)
    app.router.add_get("/api/calibration", self.handle_calibration)
    app.router.add_get("/api/network", self.handle_network)
    app.router.add_get("/api/sunnylink", self.handle_sunnylink)
    app.router.add_get("/api/storage", self.handle_storage)
    app.router.add_get("/api/speeds", self.handle_speeds)
    app.router.add_get("/api/cockpit", self.handle_cockpit)

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
    app.router.add_post("/api/update/check", self.handle_update_check)
    app.router.add_post("/api/system/reboot", self.handle_system_reboot)
    app.router.add_post("/api/system/restart", self.handle_system_restart)
    app.router.add_post("/api/system/restart-pitstop", self.handle_pitstop_restart)

    # CAN API
    app.router.add_get("/api/v1/status", self.handle_can_status)
    app.router.add_get("/api/v1/signals", self.handle_can_signals)
    app.router.add_post("/api/v1/signals/{name}", self.handle_can_signal_send)
    app.router.add_post("/api/v1/signals/batch", self.handle_can_batch_send)
    app.router.add_post("/api/v1/can/send", self.handle_can_raw_send)

    # Logs
    app.router.add_get("/api/logs/errors", self.handle_error_log)
    app.router.add_get("/api/logs", self.handle_logs)

    # OSM / Maps
    app.router.add_get("/api/osm/status", self.handle_osm_status)
    app.router.add_get("/api/osm/countries", self.handle_osm_countries)
    app.router.add_get("/api/osm/states", self.handle_osm_states)
    app.router.add_post("/api/osm/select", self.handle_osm_select)
    app.router.add_post("/api/osm/download", self.handle_osm_download)
    app.router.add_post("/api/osm/delete", self.handle_osm_delete)

    # Vehicle
    app.router.add_get("/api/vehicle", self.handle_vehicle)
    app.router.add_get("/api/vehicle/platforms", self.handle_vehicle_platforms)
    app.router.add_post("/api/vehicle/select", self.handle_vehicle_select)
    app.router.add_delete("/api/vehicle/select", self.handle_vehicle_select)
    app.router.add_get("/api/vehicle/fingerprint_diagnostics", self.handle_fingerprint_diagnostics)
    app.router.add_get("/api/vehicle/ignition_diagnostics", self.handle_ignition_diagnostics)

    # OpenAPI / Swagger
    app.router.add_get("/openapi.json", self.handle_openapi)
    app.router.add_get("/docs", self.handle_docs)

    # SPA catch-all (must be last)
    app.router.add_get("/{filename:.*}", self.handle_static)

    return app


def _setup_port_redirect():
  ipt = ["sudo", "iptables-legacy", "-t", "nat"]
  rule = ["-p", "tcp", "--dport", str(EXTERNAL_PORT), "-j", "REDIRECT", "--to-port", str(PORT)]
  subprocess.run(ipt + ["-D", "PREROUTING"] + rule, capture_output=True)
  subprocess.run(ipt + ["-A", "PREROUTING"] + rule, capture_output=True)
  subprocess.run(ipt + ["-D", "OUTPUT", "-o", "lo"] + rule, capture_output=True)
  subprocess.run(ipt + ["-A", "OUTPUT", "-o", "lo"] + rule, capture_output=True)


def main():
  logger.setLevel(logging.INFO)
  handler = logging.FileHandler("/tmp/pitstop.log")
  handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
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
