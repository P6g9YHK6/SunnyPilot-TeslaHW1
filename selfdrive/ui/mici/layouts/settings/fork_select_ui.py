import os
import subprocess

from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton
from openpilot.selfdrive.ui.mici.widgets.dialog import BigConfirmationDialog
from openpilot.system.ui.lib.application import gui_app


class ForkButton(BigButton):
  def __init__(self, key: str, org: str, repo: str, branch: str, discovered: bool = False):
    super().__init__(org, f"{repo}  {branch}", scroll=True)
    self.fork_key = key
    self._discovered = discovered


class ForkSelectUIMici(NavScroller):
  def __init__(self):
    super().__init__()
    self._forks = self._load_forks()
    for fork in self._forks:
      key = str(fork["key"]) if fork["key"] else fork.get("_key", "")
      btn = ForkButton(key, fork["org"], fork["repo"], fork["branch"], fork.get("discovered", False))
      btn.set_click_callback(lambda k=key: self._on_fork_selected(k))
      self._scroller.add_widget(btn)

  @staticmethod
  def _load_forks():
    forks = []
    try:
      with open("/data/openpilot/tools/forks.conf") as f:
        for line in f:
          line = line.strip()
          if not line or line.startswith("#"):
            continue
          parts = line.split()
          if len(parts) >= 3:
            repo_full = parts[1]
            org, repo_name = repo_full.split("/", 1) if "/" in repo_full else (repo_full, "")
            forks.append({
              "key": parts[0],
              "org": org,
              "repo": repo_name,
              "branch": parts[2],
              "discovered": False,
            })
    except Exception:
      pass

    discovered = ForkSelectUIMici._scan_discovered()
    forks.extend(discovered)
    return forks

  @staticmethod
  def _scan_discovered():
    forks_dir = "/data/forks"
    if not os.path.isdir(forks_dir):
      return []
    declared = set()
    try:
      with open("/data/openpilot/tools/forks.conf") as f:
        for line in f:
          line = line.strip()
          if not line or line.startswith("#"):
            continue
          parts = line.split()
          if len(parts) >= 3:
            declared.add(parts[1].replace("/", "_"))
    except Exception:
      pass
    discovered = []
    for entry in os.listdir(forks_dir):
      if entry in declared:
        continue
      rp = os.path.join(forks_dir, entry)
      if not os.path.isdir(rp):
        continue
      try:
        branch = subprocess.check_output(
          ["git", "-C", rp, "branch", "--show-current"],
          stderr=subprocess.DEVNULL, timeout=5,
        ).decode().strip()
      except Exception:
        branch = "unknown"
      repo_dir = entry.replace("_", "/")
      org, repo_name = repo_dir.split("/", 1) if "/" in repo_dir else (repo_dir, "")
      discovered.append({
        "key": 0,
        "org": org,
        "repo": repo_name,
        "branch": branch,
        "discovered": True,
        "_key": f"U{len(discovered) + 1}",
      })
    return discovered

  def _on_fork_selected(self, key: str):
    dlg = BigConfirmationDialog(
      "Switch Fork",
      gui_app.texture("icons_mici/settings/device/reboot.png", 64, 70),
      confirm_callback=lambda: self._switch_fork(key),
    )
    gui_app.push_widget(dlg)

  @staticmethod
  def _switch_fork(key: str):
    subprocess.Popen(
      ["bash", "/data/openpilot/tools/op.sh", "fork", key],
      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
