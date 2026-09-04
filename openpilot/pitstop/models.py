import json
import logging
import os

from aiohttp import web

from openpilot.sunnypilot.models.fetcher import ModelFetcher
from openpilot.sunnypilot.models.helpers import get_active_bundle, bundle_artifacts, verify_file, ACTIVE_BUNDLE_KEYS
from openpilot.sunnypilot.models.model_name import DEFAULT_MODEL
from openpilot.common.params import Params
from openpilot.common.hardware.hw import Paths
from openpilot.selfdrive.modeld.helpers import chestnut_present

logger = logging.getLogger("pitstop")


class ModelMixin:

  def _require_offroad(self):
    if not self.params.get_bool("IsOffroad"):
      raise web.HTTPConflict(text="Model changes are only allowed while the car is offroad")

  @staticmethod
  def _active_source_bundles(params):
    # must match main_thread's chestnut-aware fetch, or refs/indices returned here won't
    # exist in the catalog the model manager actually checks against (silent no-op select)
    fetcher = ModelFetcher(params)
    source = ModelFetcher.active_source(chestnut_present())
    return fetcher.get_bundles_for_source(source), source

  async def handle_models_list(self, request):
    try:
      bundles, _ = self._active_source_bundles(self.params)
      model_dir = Paths.model_root()
      result = []
      for b in bundles:
        d = b.to_dict()
        artifacts = bundle_artifacts(b)
        cached_files = [f for f, sha in artifacts if await verify_file(os.path.join(model_dir, f), sha)]
        d['isCached'] = bool(artifacts) and len(cached_files) == len(artifacts)
        d['cachedFiles'] = cached_files
        result.append(d)
      return web.json_response(result)
    except Exception as e:
      logger.exception("Failed to list models")
      return web.json_response({"error": str(e)}, status=500)

  async def handle_models_delete(self, request):
    self._require_offroad()
    name = request.match_info.get("name", "")
    if not name:
      raise web.HTTPBadRequest(text="Missing bundle name")
    try:
      bundles, _ = self._active_source_bundles(self.params)
    except Exception as e:
      raise web.HTTPInternalServerError(text=str(e)) from e
    bundle = next((b for b in bundles if b.internalName == name), None)
    if bundle is None:
      raise web.HTTPNotFound(text=f"Bundle '{name}' not found")
    model_dir = Paths.model_root()
    deleted = []
    for fname, _ in bundle_artifacts(bundle):
      path = os.path.join(model_dir, fname)
      if os.path.isfile(path):
        try:
          os.remove(path)
          deleted.append(fname)
        except Exception as e:
          logger.warning(f"[MODEL] failed to remove {fname}: {e}")
    for model in getattr(bundle, 'models', []):
      artifact = getattr(model, 'artifact', None)
      if artifact and getattr(artifact, 'fileName', None) and len(getattr(artifact, 'chunks', []) or []) > 0:
        manifest = os.path.join(model_dir, artifact.fileName + '.chunkmanifest')
        if os.path.isfile(manifest):
          os.remove(manifest)
          deleted.append(artifact.fileName + '.chunkmanifest')
    logger.info(f"[MODEL] deleted {name} ({len(deleted)} files)")
    return web.json_response({"status": "ok", "deleted": deleted, "bundle": name})

  async def handle_models_active(self, request):
    active = get_active_bundle(self.params)
    if active is not None:
      return web.json_response(active.to_dict())
    return web.json_response({"internalName": DEFAULT_MODEL, "displayName": DEFAULT_MODEL, "isDefault": True})

  async def handle_models_select(self, request):
    self._require_offroad()
    try:
      body = await request.json()
    except Exception:
      raise web.HTTPBadRequest(text="Invalid JSON") from None
    index = body.get("index")
    if index is None:
      raise web.HTTPBadRequest(text="Missing 'index'")
    index = int(index)
    # main_thread matches this ref against the chestnut-aware catalog; validate against
    # the same one here so a stale/mismatched index fails now instead of silently never downloading
    bundles, _ = self._active_source_bundles(self.params)
    bundle = next((b for b in bundles if b.index == index), None)
    if bundle is None:
      raise web.HTTPBadRequest(text=f"index {index} not in the current model catalog "
                                     f"(chestnut_present={chestnut_present()}); refresh the list and retry")
    if not bundle.ref:
      raise web.HTTPInternalServerError(text=f"Bundle '{bundle.internalName}' has no ref; cannot select")
    self.params.put("ModelManager_DownloadRef", bundle.ref)
    logger.info(f"[MODEL] selected index {index} (ref={bundle.ref})")
    return web.json_response({"status": "ok", "index": index})

  async def handle_models_select_default(self, request):
    self._require_offroad()
    source = ModelFetcher.active_source(chestnut_present())
    self.params.remove(ACTIVE_BUNDLE_KEYS[source])
    logger.info(f"[MODEL] reset to default ({source})")
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
    self.params.remove("ModelManager_DownloadRef")
    logger.info("[MODEL] download cancelled")
    return web.json_response({"status": "ok"})

  async def handle_models_refresh(self, request):
    for _, suffix in ModelFetcher.MODEL_SOURCES.values():
      self.params.remove(f"ModelManager_LastSyncTime{suffix}")
    logger.info("[MODEL] refresh triggered")
    return web.json_response({"status": "ok"})

  async def handle_models_cache_clear(self, request):
    self._require_offroad()
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
