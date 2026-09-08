"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""

# Self-heal for the legacy 'stock' model runner's static .pkl files
# (openpilot/selfdrive/modeld/models/*), called by openpilot/system/updated/updated.py
# when finalizing an update. These files are gitignored, so excluding them from
# git-clean (see updated.py's fetch_update()) only proves they SURVIVED an update -
# not that they're still compatible with a tinygrad_repo pin the same update may have
# just bumped. verify_and_refresh_static_models() checks a real load and, if that
# fails, fetches a verified-compatible replacement from the public defaults manifest.

import json
import os
import subprocess
import time
from pathlib import Path

import requests
from requests.exceptions import RequestException

from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.common.file_chunker import get_chunk_name, get_manifest_path
from openpilot.sunnypilot.models.helpers import _verify_file

DEFAULT_MODELS_MANIFEST_URLS = {
  "small": "https://huggingface.co/datasets/sunnypilot/sunnypilot_models_v1/resolve/main/models/defaults/small/default_models.json",
  "dm": "https://huggingface.co/datasets/sunnypilot/sunnypilot_models_v1/resolve/main/models/defaults/dm/default_models.json",
  "big": "https://huggingface.co/datasets/sunnypilot/sunnypilot_models_v1/resolve/main/models/defaults/big/default_models.json",
}

_LOAD_DRIVING = ("import sys; from openpilot.common.file_chunker import open_file_chunked; "
                  "from openpilot.selfdrive.modeld.helpers import load_oob; "
                  "load_oob(open_file_chunked(sys.argv[1]))")
_LOAD_DM = ("import sys, pickle; from openpilot.common.file_chunker import open_file_chunked; "
            "pickle.load(open_file_chunked(sys.argv[1]))")


class ModelProvisioningError(Exception):
  pass


def _fetch_manifest(kind: str) -> dict:
  try:
    r = requests.get(DEFAULT_MODELS_MANIFEST_URLS[kind], timeout=15)
    r.raise_for_status()
    return r.json()
  except (RequestException, ValueError) as e:
    raise ModelProvisioningError(f"failed to fetch default models manifest '{kind}': {e}") from e


def _download_artifact(artifact: dict, dest_path: Path) -> None:
  chunks = artifact.get("chunks") or []
  dest_path.parent.mkdir(parents=True, exist_ok=True)
  if chunks:
    n = len(chunks)
    for i, chunk in enumerate(chunks):
      p = Path(get_chunk_name(str(dest_path), i, n))
      if _verify_file(str(p), chunk["sha256"]):
        continue
      resp = requests.get(chunk["url"], stream=True, timeout=(30, 30))
      resp.raise_for_status()
      with open(p, "wb") as f:
        for data in resp.iter_content(chunk_size=8 * 1024 * 1024):
          f.write(data)
      if not _verify_file(str(p), chunk["sha256"]):
        raise ModelProvisioningError(f"sha256 mismatch after download: {p}")
    Path(get_manifest_path(str(dest_path))).write_text(str(n))
    if dest_path.is_file():
      dest_path.unlink()
  else:
    uri = artifact["download_uri"]
    if _verify_file(str(dest_path), uri["sha256"]):
      return
    resp = requests.get(uri["url"], stream=True, timeout=(30, 30))
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
      for data in resp.iter_content(chunk_size=8 * 1024 * 1024):
        f.write(data)
    if not _verify_file(str(dest_path), uri["sha256"]):
      raise ModelProvisioningError(f"sha256 mismatch after download: {dest_path}")


def _tinygrad_commit(checkout_dir: str) -> str:
  return subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=os.path.join(checkout_dir, "tinygrad_repo"), encoding="utf8"
  ).strip()


def _exists_chunked(pkl_path: Path) -> bool:
  """Mirrors open_file_chunked()'s own existence check: a model may be stored as
  <path>.chunkmanifest + <path>.chunkNNofNN rather than a plain <path>, so a naive
  pkl_path.exists() incorrectly reports every chunked model as missing."""
  return os.path.isfile(get_manifest_path(str(pkl_path))) or pkl_path.is_file()


# Substrings from tinygrad's AMD/PCIe device backend when chestnut hardware isn't
# physically linked up - this is a hardware-availability failure, not a pickle/
# tinygrad-version incompatibility, and can't be fixed by installing a different
# model file. Only relevant to the "big"/chestnut target (load_oob() for that model
# allocates the real device as part of loading, unlike the small/dm CPU-side targets).
_HARDWARE_UNAVAILABLE_MARKERS = (
  "PCIe link not up", "No interface for", "RuntimeError: no pcie", "/dev/kfd",
)

# _try_load()'s outcome: "ok" loaded cleanly; "hardware_unavailable" failed for a
# reason unrelated to the pickle itself (see above) - inconclusive, don't refresh or
# fail the update over it; "failed" is everything else (missing, or a genuine
# deserialization/version incompatibility) - the case that should trigger a refresh.
def _try_load(checkout_dir: str, pkl_path: Path, loader_snippet: str) -> str:
  """Attempts a real load of pkl_path using checkout_dir's OWN just-synced .venv and
  tinygrad_repo pin, isolated in a subprocess so a bad pickle can't crash the caller."""
  python = os.path.join(checkout_dir, ".venv", "bin", "python3")
  if not os.path.isfile(python) or not _exists_chunked(pkl_path):
    return "failed"
  try:
    subprocess.run([python, "-c", loader_snippet, str(pkl_path)], cwd=checkout_dir,
                    env={**os.environ, "PYTHONPATH": checkout_dir},
                    check=True, capture_output=True, timeout=120)
    return "ok"
  except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
    stderr = getattr(e, "stderr", b"")
    stderr_text = stderr.decode("utf8", errors="replace") if isinstance(stderr, bytes) else str(stderr)
    if any(marker in stderr_text for marker in _HARDWARE_UNAVAILABLE_MARKERS):
      cloudlog.warning(f"{pkl_path}: chestnut hardware not available/linked, skipping compatibility check")
      return "hardware_unavailable"
    cloudlog.warning(f"model load check failed for {pkl_path}: {stderr_text}")
    return "failed"


def verify_and_refresh_static_models(checkout_dir: str, chestnut: bool = False) -> None:
  """Called by finalize_update() AFTER sync_venv(checkout_dir). Raises
  ModelProvisioningError on unrecoverable failure - the caller must treat that as
  fatal for this update attempt (do not mark it ready-to-swap).

  On success, records a per-source outcome ("ok" = was already fine, "refreshed" =
  had to be re-fetched, "hardware_unavailable" = chestnut not linked, so unverified
  either way) to the ModelStaticProvisioningStatus param, purely so pitstop can show
  a "your default model was auto-repaired after the last update" transparency note.
  Only written on success - a raised exception means this candidate never becomes
  the running checkout, so there is nothing true to report yet."""
  from openpilot.selfdrive.modeld.helpers import modeld_pkl_path
  pkl_dir = Path(checkout_dir) / "openpilot/selfdrive/modeld/models"

  targets = [(Path(modeld_pkl_path(False)).name, _LOAD_DRIVING, "small"),
             ("dmonitoring_model_tinygrad.pkl", _LOAD_DM, "dm")]
  if chestnut:
    targets.append((Path(modeld_pkl_path(True)).name, _LOAD_DRIVING, "big"))

  outcomes: dict[str, str] = {}
  for fname, loader, kind in targets:
    pkl_path = pkl_dir / fname
    result = _try_load(checkout_dir, pkl_path, loader)
    if result in ("ok", "hardware_unavailable"):
      outcomes[kind] = result
      continue

    cloudlog.warning(f"{pkl_path} missing/incompatible with new tinygrad pin; refreshing from '{kind}' manifest")
    manifest = _fetch_manifest(kind)
    if manifest.get("tinygrad_ref") != _tinygrad_commit(checkout_dir):
      raise ModelProvisioningError(
        f"default-models manifest tinygrad_ref does not match {checkout_dir}'s tinygrad_repo "
        f"pin; refusing to install a known-incompatible model")
    artifact = manifest["bundles"][0]["models"][0]["artifact"]
    _download_artifact(artifact, pkl_path)
    result = _try_load(checkout_dir, pkl_path, loader)
    if result == "failed":
      raise ModelProvisioningError(f"freshly-downloaded {pkl_path} still fails to load")
    outcomes[kind] = "refreshed" if result == "ok" else result

  Params().put("ModelStaticProvisioningStatus", json.dumps({"outcomes": outcomes, "ts": time.time()}))
