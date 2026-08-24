import hashlib
import json
import logging
import os

from openpilot.common.params import ParamKeyType

from .constants import STATIC_DIR

logger = logging.getLogger("pitstop")


class UtilMixin:

  @staticmethod
  def _hash_static():
    h = hashlib.md5()
    for f in ('app.js', 'index.html', 'style.css'):
      p = os.path.join(STATIC_DIR, f)
      try:
        with open(p, 'rb') as fh:
          h.update(fh.read())
      except FileNotFoundError:
        pass
    return h.hexdigest()[:8]

  @staticmethod
  def _param_to_str(raw) -> str:
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
    try:
      current = self.params.get(key)
    except Exception as e:
      raise ValueError(f"Unknown param '{key}'") from e

    sv = str(str_value)
    if isinstance(current, bool) or (current is None and sv in ("0", "1")):
      self.params.put_bool(key, sv in ("1", "true", "yes"))
      logger.debug(f"[PARAM] {key} -> bool({sv in ('1', 'true', 'yes')})")
    elif isinstance(current, int):
      self.params.put(key, int(sv))
      logger.debug(f"[PARAM] {key} -> int({sv})")
    elif isinstance(current, float):
      self.params.put(key, float(sv))
      logger.debug(f"[PARAM] {key} -> float({sv})")
    elif isinstance(current, (dict, list)):
      self.params.put(key, json.loads(sv))
      logger.debug(f"[PARAM] {key} -> json({sv})")
    elif isinstance(current, bytes):
      self.params.put(key, sv.encode("utf-8"))
      logger.debug(f"[PARAM] {key} -> bytes({sv})")
    elif current is None:
      ptype = self.params.get_type(key)
      if ptype == ParamKeyType.FLOAT:
        self.params.put(key, float(sv))
        logger.debug(f"[PARAM] {key} -> float({sv}) (type=FLOAT)")
      elif ptype == ParamKeyType.INT:
        self.params.put(key, int(sv))
        logger.debug(f"[PARAM] {key} -> int({sv}) (type=INT)")
      elif ptype == ParamKeyType.BOOL:
        self.params.put_bool(key, sv in ("1", "true", "yes"))
        logger.debug(f"[PARAM] {key} -> bool({sv in ('1', 'true', 'yes')}) (type=BOOL)")
      else:
        self.params.put(key, sv)
        logger.debug(f"[PARAM] {key} -> str({sv}) (type=other)")
    else:
      self.params.put(key, sv)
      logger.debug(f"[PARAM] {key} -> str({sv}) (fallback)")
