import json
import logging
import os

from aiohttp import web

from openpilot.sunnypilot.models.fetcher import ModelFetcher
from openpilot.sunnypilot.models.helpers import get_active_bundle
from openpilot.sunnypilot.models.model_name import DEFAULT_MODEL
from openpilot.common.params import Params
from openpilot.system.hardware.hw import Paths

logger = logging.getLogger("pitstop")


class ModelMixin:

  @staticmethod
  def _model_file_cached(model_dir, fname):
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
      if os.path.isfile(base):
        os.remove(base)
        deleted.append(fname)
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
            try:
              os.remove(chunk)
              deleted.append(os.path.basename(chunk))
            except Exception as e:
              logger.warning(f"[MODEL] failed to remove chunk {chunk}: {e}")
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
