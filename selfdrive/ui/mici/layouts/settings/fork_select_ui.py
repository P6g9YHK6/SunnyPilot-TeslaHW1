import os
import subprocess

from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton
from openpilot.selfdrive.ui.mici.widgets.dialog import BigConfirmationDialog
from openpilot.system.ui.lib.application import gui_app


class ForkButton(BigButton):
  def __init__(self, key: str, display: str, comment: str = ""):
    super().__init__(display, comment, scroll=True)
    self.fork_key = key


class ForkSelectUIMici(NavScroller):
  def __init__(self):
    super().__init__()
    self._forks = self._load_forks()
    for fork in self._forks:
      btn = ForkButton(fork["key"], fork["display"], fork.get("comment", ""))
      btn.set_click_callback(lambda key=fork["key"]: self._on_fork_selected(key))
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
            forks.append({
              "key": parts[0],
              "display": f"{parts[1]}:{parts[2]}",
              "comment": " ".join(parts[3:]) if len(parts) > 3 else "",
            })
    except Exception:
      pass
    return forks

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
