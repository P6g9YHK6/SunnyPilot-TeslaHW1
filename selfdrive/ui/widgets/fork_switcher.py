import os
import re
import subprocess
import threading
from collections.abc import Callable

import pyray as rl

from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.widgets.button import Button, ButtonStyle
from openpilot.system.ui.widgets.list_view import (
  BUTTON_BORDER_RADIUS, BUTTON_FONT_SIZE,
)

FORK_ROW_HEIGHT = 130
FORK_ROW_FONT_SIZE = 45
FORK_ROW_SUB_FONT_SIZE = 32
FORK_ROW_SPACING = 5
DRAG_THRESHOLD = 20
LIST_MARGIN = 50
CLOSE_BUTTON_HEIGHT = 120
CLOSE_BUTTON_WIDTH = 300
HEADER_HEIGHT = 100
HEADER_FONT_SIZE = 55
SECTION_HEADER_HEIGHT = 50
SECTION_HEADER_FONT_SIZE = 35


def _find_openpilot_root() -> str | None:
  current = os.path.dirname(os.path.abspath(__file__))
  for _ in range(10):
    if os.path.isfile(os.path.join(current, "launch_openpilot.sh")):
      return current
    parent = os.path.dirname(current)
    if parent == current:
      break
    current = parent
  for d in ["/data/openpilot", os.path.expanduser("~/openpilot")]:
    if os.path.isfile(os.path.join(d, "launch_openpilot.sh")):
      return d
  return None


def _parse_forks_conf() -> list[dict]:
  root = _find_openpilot_root()
  if root is None:
    return []
  conf_path = os.path.join(root, "tools", "forks.conf")
  if not os.path.isfile(conf_path):
    return []
  forks = []
  pattern = re.compile(r'^\s*(\d+)\s+(\S+?)/(\S+?)\s+(\S+)\s*(.*)$')
  with open(conf_path) as f:
    for line in f:
      m = pattern.match(line)
      if m:
        forks.append({
          "num": int(m.group(1)),
          "org": m.group(2),
          "repo": m.group(3),
          "branch": m.group(4),
          "comment": m.group(5).strip(),
          "discovered": False,
        })
  forks.sort(key=lambda x: x["num"])
  return forks


def _scan_discovered_forks() -> list[dict]:
  forks_dir = "/data/forks"
  if not os.path.isdir(forks_dir):
    return []
  declared = set()
  root = _find_openpilot_root()
  if root is not None:
    conf_path = os.path.join(root, "tools", "forks.conf")
    if os.path.isfile(conf_path):
      pattern = re.compile(r'^\s*\d+\s+(\S+?/\S+?)\s+\S+')
      with open(conf_path) as f:
        for line in f:
          m = pattern.match(line)
          if m:
            declared.add(m.group(1).replace("/", "_"))
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
      "num": 0,
      "org": org,
      "repo": repo_name,
      "branch": branch,
      "comment": "",
      "discovered": True,
    })
  return discovered


def _exec_fork_switch(fork_num: int, repo: str, branch: str, status_callback: Callable[[str], None], done_callback: Callable[[bool, str], None]):
  def run():
    try:
      root = _find_openpilot_root()
      if root is None:
        done_callback(False, "Cannot find openpilot root")
        return

      repo_key = repo.replace("/", "_")
      forks_dir = "/data/forks"
      rp = os.path.join(forks_dir, repo_key)

      os.makedirs(forks_dir, exist_ok=True)

      if not os.path.isdir(rp):
        status_callback(tr("Cloning repository..."))
        url = f"https://github.com/{repo}.git"
        subprocess.run(
          ["git", "clone", "-b", branch, "--depth", "1", "--single-branch",
           "--recurse-submodules", "--shallow-submodules", url, rp],
          capture_output=True, text=True, check=True, timeout=300,
        )
      else:
        status_callback(tr("Fetching updates..."))
        subprocess.run(
          ["git", "-C", rp, "fetch", "origin", f"{branch}:{branch}", "--depth", "1"],
          capture_output=True, text=True, check=True, timeout=120,
        )
        subprocess.run(
          ["git", "-C", rp, "checkout", "-f", branch],
          capture_output=True, text=True, check=True, timeout=30,
        )
        subprocess.run(
          ["git", "-C", rp, "submodule", "update", "--init", "--recursive"],
          capture_output=True, text=True, check=True, timeout=300,
        )

      status_callback(tr("Updating symlink..."))
      if os.path.islink("/data/openpilot"):
        os.unlink("/data/openpilot")
      elif os.path.isdir("/data/openpilot"):
        bak = f"/data/openpilot.orig.{int(__import__('time').time())}"
        os.rename("/data/openpilot", bak)
      os.symlink(rp, "/data/openpilot")

      done_callback(True, tr("Rebooting..."))
      subprocess.run(["sudo", "reboot"], check=False)
    except subprocess.CalledProcessError as e:
      msg = e.stderr or str(e)
      done_callback(False, msg)
    except Exception as e:
      done_callback(False, str(e))

  thread = threading.Thread(target=run, daemon=True)
  thread.start()


class ForkListWidget(Widget):
  def __init__(self, forks: list[dict], callback: Callable[[int, str, str], None]):
    super().__init__()
    self._declared = [f for f in forks if not f.get("discovered")]
    self._discovered = _scan_discovered_forks()
    self._all_forks = self._declared + self._discovered
    self._callback = callback
    self._font = gui_app.font(FontWeight.NORMAL)
    self._sub_font = gui_app.font(FontWeight.NORMAL)
    self._header_font = gui_app.font(FontWeight.BOLD)

    self._scroll_offset = 0
    self._drag_start_y = None
    self._hit_rects = {}
    self._last_mouse_y = None

    self._close_button = Button(
      tr("Close"),
      click_callback=self._close,
      button_style=ButtonStyle.NORMAL,
      font_size=BUTTON_FONT_SIZE,
      border_radius=BUTTON_BORDER_RADIUS,
    )

  def _close(self):
    gui_app.pop_widget()

  def _get_total_content_height(self):
    total = len(self._declared) * (FORK_ROW_HEIGHT + FORK_ROW_SPACING)
    if self._discovered:
      total += SECTION_HEADER_HEIGHT + len(self._discovered) * (FORK_ROW_HEIGHT + FORK_ROW_SPACING)
    return total

  def _render(self, rect: rl.Rectangle):
    content_x = rect.x + LIST_MARGIN
    content_width = rect.width - LIST_MARGIN * 2
    header_y = rect.y + 20

    rl.draw_text_ex(self._header_font, tr("Select a Fork"),
                    rl.Vector2(content_x, header_y), HEADER_FONT_SIZE, 0, rl.WHITE)

    list_top = header_y + HEADER_HEIGHT
    list_bottom = rect.y + rect.height - CLOSE_BUTTON_HEIGHT - LIST_MARGIN
    list_height = list_bottom - list_top

    total_content_height = self._get_total_content_height()
    scroll_offset = max(0, min(self._scroll_offset, max(0, total_content_height - list_height)))

    y = list_top - scroll_offset
    mouse_pos = rl.get_mouse_position()
    idx = 0
    for fork in self._declared:
      row_rect = rl.Rectangle(content_x, y, content_width, FORK_ROW_HEIGHT)
      row_bottom = y + FORK_ROW_HEIGHT
      if row_bottom > rect.y and y < list_bottom:
        hovered = rl.check_collision_point_rec(mouse_pos, row_rect)
        bg_color = rl.Color(57, 57, 57, 255) if not hovered else rl.Color(74, 74, 74, 255)
        rl.draw_rectangle_rounded(row_rect, 0.3, 10, bg_color)

        rl.draw_text_ex(self._font, fork["org"], rl.Vector2(content_x + 15, y + 10),
                        FORK_ROW_FONT_SIZE, 0, rl.WHITE)
        rl.draw_text_ex(self._sub_font, fork["repo"], rl.Vector2(content_x + 15, y + FORK_ROW_FONT_SIZE + 10),
                        FORK_ROW_SUB_FONT_SIZE, 0, rl.Color(170, 170, 170, 255))
        rl.draw_text_ex(self._sub_font, fork["branch"], rl.Vector2(content_x + 15, y + FORK_ROW_FONT_SIZE + FORK_ROW_SUB_FONT_SIZE + 5),
                        FORK_ROW_SUB_FONT_SIZE, 0, rl.Color(200, 200, 200, 255))

        self._hit_rects[idx] = row_rect
      y += FORK_ROW_HEIGHT + FORK_ROW_SPACING
      idx += 1

    if self._discovered:
      if y + SECTION_HEADER_HEIGHT > rect.y and y < list_bottom:
        rl.draw_text_ex(self._sub_font, tr("--- Discovered Forks ---"),
                        rl.Vector2(content_x + 15, y + 10), SECTION_HEADER_FONT_SIZE, 0, rl.Color(128, 128, 128, 255))
      y += SECTION_HEADER_HEIGHT

      for fork in self._discovered:
        row_rect = rl.Rectangle(content_x, y, content_width, FORK_ROW_HEIGHT)
        row_bottom = y + FORK_ROW_HEIGHT
        if row_bottom > rect.y and y < list_bottom:
          hovered = rl.check_collision_point_rec(mouse_pos, row_rect)
          bg_color = rl.Color(50, 50, 60, 255) if not hovered else rl.Color(65, 65, 75, 255)
          rl.draw_rectangle_rounded(row_rect, 0.3, 10, bg_color)

          rl.draw_text_ex(self._sub_font, tr("(untracked)"),
                          rl.Vector2(content_x + 15, y + 8), FORK_ROW_SUB_FONT_SIZE - 4, 0, rl.Color(200, 150, 50, 255))
          rl.draw_text_ex(self._font, fork["org"], rl.Vector2(content_x + 15, y + 28),
                          FORK_ROW_FONT_SIZE, 0, rl.WHITE)
          rl.draw_text_ex(self._sub_font, fork["repo"], rl.Vector2(content_x + 15, y + FORK_ROW_FONT_SIZE + 20),
                          FORK_ROW_SUB_FONT_SIZE, 0, rl.Color(170, 170, 170, 255))
          rl.draw_text_ex(self._sub_font, fork["branch"], rl.Vector2(content_x + 15, y + FORK_ROW_FONT_SIZE + FORK_ROW_SUB_FONT_SIZE + 10),
                          FORK_ROW_SUB_FONT_SIZE, 0, rl.Color(200, 200, 200, 255))

          self._hit_rects[idx] = row_rect
        y += FORK_ROW_HEIGHT + FORK_ROW_SPACING
        idx += 1

    if total_content_height > list_height:
      bar_height = max(30, list_height * list_height / total_content_height)
      bar_y = list_top + (list_height - bar_height) * scroll_offset / (total_content_height - list_height)
      rl.draw_rectangle_rounded(rl.Rectangle(rect.x + rect.width - 10, bar_y, 6, bar_height), 1.0, 10, rl.Color(128, 128, 128, 128))

    close_y = rect.y + rect.height - CLOSE_BUTTON_HEIGHT - LIST_MARGIN
    close_x = rect.x + (rect.width - CLOSE_BUTTON_WIDTH) / 2
    self._close_button.set_rect(rl.Rectangle(close_x, close_y, CLOSE_BUTTON_WIDTH, CLOSE_BUTTON_HEIGHT))
    self._close_button.render(rl.Rectangle(close_x, close_y, CLOSE_BUTTON_WIDTH, CLOSE_BUTTON_HEIGHT))

  def show_event(self):
    super().show_event()
    self._scroll_offset = 0
    self._last_mouse_y = None

  def _handle_mouse_press(self, mouse_pos):
    self._drag_start_y = mouse_pos.y
    self._last_mouse_y = mouse_pos.y

  def _handle_mouse_release(self, mouse_pos):
    drag_dist = abs(mouse_pos.y - self._drag_start_y) if self._drag_start_y is not None else 0
    self._drag_start_y = None
    self._last_mouse_y = None
    if drag_dist > DRAG_THRESHOLD:
      return
    for idx, row_rect in self._hit_rects.items():
      if rl.check_collision_point_rec(mouse_pos, row_rect):
        fork = self._all_forks[idx]
        gui_app.pop_widget()
        self._callback(fork["num"], f"{fork['org']}/{fork['repo']}", fork["branch"])
        return

  def _handle_mouse_event(self, mouse_event):
    if self._last_mouse_y is not None:
      delta = mouse_event.pos.y - self._last_mouse_y
      total_content = self._get_total_content_height()
      list_top = self._rect.y + HEADER_HEIGHT + 20
      list_bottom = self._rect.y + self._rect.height - CLOSE_BUTTON_HEIGHT - LIST_MARGIN
      list_height = list_bottom - list_top
      max_scroll = max(0, total_content - list_height)
      self._scroll_offset = max(0, min(self._scroll_offset - delta, max_scroll))
      self._last_mouse_y = mouse_event.pos.y


class ForkSwitchExecuting(Widget):
  def __init__(self, fork_num: int, repo: str, branch: str):
    super().__init__()
    self._status = tr("Starting...")
    self._done = False
    self._success = False
    self._message = ""
    self._font = gui_app.font(FontWeight.NORMAL)
    self._title_font = gui_app.font(FontWeight.BOLD)
    _exec_fork_switch(fork_num, f"{repo}", branch, self._set_status, self._on_done)

  def _set_status(self, status: str):
    self._status = status

  def _on_done(self, success: bool, message: str):
    self._done = True
    self._success = success
    self._message = message

  def _render(self, rect: rl.Rectangle):
    center_x = rect.x + rect.width / 2
    center_y = rect.y + rect.height / 2

    if self._done:
      if self._success:
        rl.draw_text_ex(self._title_font, self._message,
                        rl.Vector2(center_x - 100, center_y - 30), 50, 0, rl.Color(51, 171, 76, 255))
      else:
        rl.draw_text_ex(self._title_font, tr("Error"),
                        rl.Vector2(center_x - 50, center_y - 60), 55, 0, rl.Color(226, 44, 44, 255))
        rl.draw_text_ex(self._font, self._message[:80],
                        rl.Vector2(center_x - 200, center_y), 35, 0, rl.WHITE)
        close_y = center_y + 80
        btn = Button(tr("OK"), click_callback=lambda: gui_app.pop_widget(),
                     button_style=ButtonStyle.NORMAL, font_size=BUTTON_FONT_SIZE,
                     border_radius=BUTTON_BORDER_RADIUS)
        btn.set_rect(rl.Rectangle(center_x - 100, close_y, 200, 80))
        btn.render(rl.Rectangle(center_x - 100, close_y, 200, 80))
    else:
      rl.draw_text_ex(self._title_font, tr("Switching Fork..."),
                      rl.Vector2(center_x - 120, center_y - 40), 50, 0, rl.WHITE)
      rl.draw_text_ex(self._font, self._status,
                      rl.Vector2(center_x - 150, center_y + 20), 35, 0, rl.Color(170, 170, 170, 255))



