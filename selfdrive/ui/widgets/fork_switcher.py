import os
import re
import subprocess
import threading
from collections.abc import Callable

import pyray as rl

from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.button import Button, ButtonStyle
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
from openpilot.system.ui.widgets.list_view import (
  ItemAction, ListItem, BUTTON_HEIGHT, BUTTON_BORDER_RADIUS, BUTTON_FONT_SIZE, BUTTON_WIDTH,
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


def _parse_forks_conf() -> list[tuple[int, str, str, str]]:
  root = _find_openpilot_root()
  if root is None:
    return []
  conf_path = os.path.join(root, "tools", "forks.conf")
  if not os.path.isfile(conf_path):
    return []
  forks = []
  pattern = re.compile(r'^\s*(\d+)\s+(\S+?/\S+?)\s+(\S+)\s*(.*)$')
  with open(conf_path) as f:
    for line in f:
      m = pattern.match(line)
      if m:
        num = int(m.group(1))
        repo = m.group(2)
        branch = m.group(3)
        comment = m.group(4).strip()
        forks.append((num, repo, branch, comment))
  forks.sort(key=lambda x: x[0])
  return forks


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
  def __init__(self, forks: list[tuple[int, str, str, str]], callback: Callable[[int, str, str], None]):
    super().__init__()
    self._forks = forks
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

  def _render(self, rect: rl.Rectangle):
    content_x = rect.x + LIST_MARGIN
    content_width = rect.width - LIST_MARGIN * 2
    header_y = rect.y + 20

    rl.draw_text_ex(self._header_font, tr("Select a Fork"),
                    rl.Vector2(content_x, header_y), HEADER_FONT_SIZE, 0, rl.WHITE)

    list_top = header_y + HEADER_HEIGHT
    list_bottom = rect.y + rect.height - CLOSE_BUTTON_HEIGHT - LIST_MARGIN
    list_height = list_bottom - list_top

    total_content_height = len(self._forks) * (FORK_ROW_HEIGHT + FORK_ROW_SPACING)
    scroll_offset = max(0, min(self._scroll_offset, max(0, total_content_height - list_height)))

    y = list_top - scroll_offset
    mouse_pos = rl.get_mouse_position()

    for idx, (num, repo, branch, comment) in enumerate(self._forks):
      row_rect = rl.Rectangle(content_x, y, content_width, FORK_ROW_HEIGHT)
      row_bottom = y + FORK_ROW_HEIGHT

      if row_bottom > rect.y and y < list_bottom:
        hovered = rl.check_collision_point_rec(mouse_pos, row_rect)
        bg_color = rl.Color(57, 57, 57, 255) if not hovered else rl.Color(74, 74, 74, 255)
        rl.draw_rectangle_rounded(row_rect, 0.3, 10, bg_color)

        label = f"{num}  {repo}  {branch}"
        rl.draw_text_ex(self._font, label, rl.Vector2(content_x + 15, y + 10), FORK_ROW_FONT_SIZE, 0, rl.WHITE)

        if comment:
          rl.draw_text_ex(self._sub_font, comment, rl.Vector2(content_x + 15, y + FORK_ROW_FONT_SIZE + 15),
                          FORK_ROW_SUB_FONT_SIZE, 0, rl.Color(170, 170, 170, 255))

        self._hit_rects[idx] = row_rect

      y += FORK_ROW_HEIGHT + FORK_ROW_SPACING

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
        num, repo, branch, _ = self._forks[idx]
        gui_app.pop_widget()
        self._callback(num, repo, branch)
        return

  def _handle_mouse_event(self, mouse_event):
    if self._last_mouse_y is not None:
      delta = mouse_event.pos.y - self._last_mouse_y
      total_content = len(self._forks) * (FORK_ROW_HEIGHT + FORK_ROW_SPACING)
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
    _exec_fork_switch(fork_num, repo, branch, self._set_status, self._on_done)

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


class ForkSwitcherAction(ItemAction):
  def __init__(self, enabled: bool | Callable[[], bool] = True):
    super().__init__(width=BUTTON_WIDTH, enabled=enabled)
    self._button = Button(
      lambda: tr("SELECT"),
      click_callback=self._on_select,
      font_size=BUTTON_FONT_SIZE,
      font_weight=FontWeight.MEDIUM,
      button_style=ButtonStyle.LIST_ACTION,
      border_radius=BUTTON_BORDER_RADIUS,
    )

  def set_touch_valid_callback(self, touch_callback: Callable[[], bool]):
    super().set_touch_valid_callback(touch_callback)
    self._button.set_touch_valid_callback(touch_callback)

  def _on_select(self):
    forks = _parse_forks_conf()
    if not forks:
      gui_app.push_widget(alert_dialog(tr("No forks found in tools/forks.conf")))
      return

    def on_fork_selected(num, repo, branch):
      def on_confirm(result):
        if result == DialogResult.CONFIRM:
          gui_app.push_widget(ForkSwitchExecuting(num, repo, branch))

      title = f"Switch to {repo}:{branch}?"
      desc = (f"<b>Fork:</b> {repo}<br>"
              f"<b>Branch:</b> {branch}<br><br>"
              f"{'This will reboot the device.' if os.getenv('DEVICE') != 'pc' else 'This will switch the fork.'}")
      dlg = ConfirmDialog(desc, tr("Switch & Reboot"), rich=True, callback=on_confirm)
      gui_app.push_widget(dlg)

    gui_app.push_widget(ForkListWidget(forks, on_fork_selected))

  def _render(self, rect: rl.Rectangle):
    self._button.set_enabled(self.enabled)
    button_rect = rl.Rectangle(
      rect.x + rect.width - BUTTON_WIDTH,
      rect.y + (rect.height - BUTTON_HEIGHT) / 2,
      BUTTON_WIDTH, BUTTON_HEIGHT,
    )
    self._button.set_rect(button_rect)
    self._button.render(button_rect)


def fork_switcher_item(enabled: bool | Callable[[], bool] = True) -> ListItem:
  action = ForkSwitcherAction(enabled=enabled)
  return ListItem(
    title=lambda: tr("Switch Fork"),
    description=lambda: tr("Choose a fork to switch to. This will reboot the device."),
    action_item=action,
  )
