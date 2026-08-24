import json
import logging
import os
import time

from aiohttp import web

from openpilot.system.hardware.hw import Paths
from openpilot.common.params import Params

from .constants import PITSTOP_DATA_DIR

logger = logging.getLogger("pitstop")


class OsmMixin:

  def _osm_get_cache_path(self, name: str) -> str:
    return os.path.join(PITSTOP_DATA_DIR, f"osm_{name}.json")

  def _osm_load_cached(self, name: str) -> dict | None:
    cache_path = self._osm_get_cache_path(name)
    if os.path.isfile(cache_path):
      try:
        with open(cache_path) as f:
          return json.load(f)
      except Exception:
        pass
    return None

  def _osm_save_cache(self, name: str, data: dict) -> None:
    cache_path = self._osm_get_cache_path(name)
    try:
      with open(cache_path, "w") as f:
        json.dump(data, f)
    except Exception:
      pass

  def _osm_cache_expired(self, name: str, max_age_seconds: int = 86400) -> bool:
    cache_path = self._osm_get_cache_path(name)
    if not os.path.isfile(cache_path):
      return True
    try:
      mtime = os.path.getmtime(cache_path)
      return (time.time() - mtime) > max_age_seconds
    except Exception:
      return True

  def _osm_fetch_remote(self, url: str) -> dict | None:
    try:
      import urllib.request
      with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode())
    except Exception:
      return None

  def _get_map_size(self) -> int:
    total_size = 0
    map_root = Paths.mapd_root()
    offline_path = os.path.join(map_root, "offline") if map_root else None
    if offline_path and os.path.isdir(offline_path):
      for dirpath, _, filenames in os.walk(offline_path):
        for f in filenames:
          fp = os.path.join(dirpath, f)
          try:
            total_size += os.path.getsize(fp)
          except Exception:
            pass
    return total_size

  async def handle_osm_status(self, request):
    progress = self.params.get("OSMDownloadProgress")
    download_progress = None
    if progress:
      try:
        download_progress = {
          "total_files": progress.get("total_files", 0) if isinstance(progress, dict) else 0,
          "downloaded_files": progress.get("downloaded_files", 0) if isinstance(progress, dict) else 0,
        }
      except Exception:
        download_progress = None
    downloading = bool(self.params.get("OSMDownloadLocations"))
    country = self.params.get("OsmLocationName") or ""
    state = self.params.get("OsmStateName") or ""
    country_title = self.params.get("OsmLocationTitle") or ""
    state_title = self.params.get("OsmStateTitle") or ""
    ts = self.params.get("OsmDownloadedDate")
    last_checked = None
    if ts:
      try:
        ts_f = float(ts)
        if ts_f > 0:
          last_checked = ts_f
      except Exception:
        pass
    return web.json_response({
      "version": self.params.get("MapdVersion") or "Unknown",
      "country": country, "country_title": country_title,
      "state": state, "state_title": state_title,
      "size_bytes": self._get_map_size(),
      "downloading": downloading, "progress": download_progress,
      "last_checked": last_checked,
    })

  async def handle_osm_countries(self, request):
    cache_name = "countries"
    if self._osm_cache_expired(cache_name):
      url = "https://raw.githubusercontent.com/pfeiferj/openpilot-mapd/main/nation_bounding_boxes.json"
      data = self._osm_fetch_remote(url)
      if data:
        self._osm_save_cache(cache_name, data)
      else:
        cached = self._osm_load_cached(cache_name)
        if cached:
          return web.json_response(cached)
        return web.json_response({"error": "Failed to fetch countries"}, status=503)
    else:
      data = self._osm_load_cached(cache_name)
      if data:
        return web.json_response(data)
      return web.json_response({"error": "Cache missing"}, status=503)
    return web.json_response(data)

  async def handle_osm_states(self, request):
    cache_name = "states"
    if self._osm_cache_expired(cache_name):
      url = "https://raw.githubusercontent.com/pfeiferj/openpilot-mapd/main/us_states_bounding_boxes.json"
      data = self._osm_fetch_remote(url)
      if data:
        self._osm_save_cache(cache_name, data)
      else:
        cached = self._osm_load_cached(cache_name)
        if cached:
          return web.json_response(cached)
        return web.json_response({"error": "Failed to fetch states"}, status=503)
    else:
      data = self._osm_load_cached(cache_name)
      if data:
        return web.json_response(data)
      return web.json_response({"error": "Cache missing"}, status=503)
    return web.json_response(data)

  async def handle_osm_select(self, request):
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON")
    country = body.get("country")
    state = body.get("state")
    if state:
      self.params.put("OsmStateName", state)
      self.params.remove("OsmStateTitle")
    else:
      self.params.remove("OsmStateName")
      self.params.remove("OsmStateTitle")
    if country:
      self.params.put_bool("OsmLocal", True)
      self.params.put("OsmLocationName", country)
    else:
      self.params.remove("OsmLocationName")
      self.params.remove("OsmLocationTitle")
      self.params.remove("OsmLocal")
    logger.info(f"[OSM] selected country={country} state={state}")
    return web.json_response({"status": "ok", "country": country, "state": state})

  async def handle_osm_download(self, request):
    self.params.put_bool("OsmDbUpdatesCheck", True)
    logger.info("[OSM] download triggered")
    return web.json_response({"status": "ok"})

  async def handle_osm_delete(self, request):
    import shutil
    offline_path = os.path.join(Paths.mapd_root(), "offline") if Paths.mapd_root() else None
    if offline_path and os.path.isdir(offline_path):
      try:
        shutil.rmtree(offline_path)
      except Exception:
        pass
    for param in ("OsmDownloadedDate", "OsmLocal", "OsmLocationName", "OsmLocationTitle", "OsmStateName", "OsmStateTitle"):
      self.params.remove(param)
    logger.info("[OSM] maps deleted")
    return web.json_response({"status": "ok"})
