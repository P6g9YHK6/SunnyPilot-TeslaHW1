import os
import subprocess

from openpilot.common.params import Params
from openpilot.selfdrive.ui.widgets.ssh_key import ssh_key_item
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.widgets.list_view import toggle_item, button_item
from openpilot.system.ui.widgets.scroller_tici import Scroller
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog

if gui_app.sunnypilot_ui():
  from openpilot.system.ui.sunnypilot.widgets.list_view import toggle_item_sp as toggle_item

# Description constants
DESCRIPTIONS = {
  'enable_adb': tr_noop(
    "ADB (Android Debug Bridge) allows connecting to your device over USB or over the network. " +
    "See https://docs.comma.ai/how-to/connect-to-comma for more info."
  ),
  'enable_bridge': tr_noop(
    "ZMQ Bridge allows connecting Cabana locally to stream CAN data."
  ),
  'ssh_key': tr_noop(
    "Warning: This grants SSH access to all public keys in your GitHub settings. Never enter a GitHub username " +
    "other than your own. A comma employee will NEVER ask you to add their GitHub username."
  ),
  'alpha_longitudinal': tr_noop(
    "<b>WARNING: sunnypilot longitudinal control is in alpha for this car and will disable Automatic Emergency Braking (AEB).</b><br><br>" +
    "On this car, sunnypilot defaults to the car's built-in ACC instead of sunnypilot's longitudinal control. " +
    "Enable this to switch to sunnypilot longitudinal control. " +
    "Enabling Experimental mode is recommended when enabling sunnypilot longitudinal control alpha. " +
    "Changing this setting will restart sunnypilot if the car is powered on."
  ),
}


class DeveloperLayout(Widget):
  def __init__(self):
    super().__init__()
    self._params = Params()
    self._is_release = False  # self._params.get_bool("IsReleaseBranch")

    # Load fork list from config
    self._fork_list = self._load_forks()

    # Build items and keep references for callbacks/state updates
    self._adb_toggle = toggle_item(
      lambda: tr("Enable ADB"),
      description=lambda: tr(DESCRIPTIONS["enable_adb"]),
      initial_state=self._params.get_bool("AdbEnabled"),
      callback=self._on_enable_adb,
      enabled=ui_state.is_offroad,
    )

    # SSH enable toggle + SSH key management
    self._ssh_toggle = toggle_item(
      lambda: tr("Enable SSH"),
      description="",
      initial_state=self._params.get_bool("SshEnabled"),
      callback=self._on_enable_ssh,
    )
    self._ssh_keys = ssh_key_item(lambda: tr("SSH Keys"), description=lambda: tr(DESCRIPTIONS["ssh_key"]))

    self._bridge_toggle = toggle_item(
      lambda: tr("Enable ZMQ Bridge"),
      description=lambda: tr(DESCRIPTIONS["enable_bridge"]),
      initial_state=self._params.get_bool("BridgeEnabled"),
      callback=self._on_enable_bridge,
    )

    self._fork_btn = button_item(
      lambda: tr("Fork"),
      lambda: tr(self._get_current_fork_display()),
      description=lambda: tr("Select a fork to switch to. Device will reboot."),
      callback=self._on_select_fork,
      enabled=lambda: ui_state.is_offroad,
    )

    self._joystick_toggle = toggle_item(
      lambda: tr("Joystick Debug Mode"),
      description="",
      initial_state=self._params.get_bool("JoystickDebugMode"),
      callback=self._on_joystick_debug_mode,
      enabled=ui_state.is_offroad,
    )

    self._long_maneuver_toggle = toggle_item(
      lambda: tr("Longitudinal Maneuver Mode"),
      description="",
      initial_state=self._params.get_bool("LongitudinalManeuverMode"),
      callback=self._on_long_maneuver_mode,
    )

    self._lat_maneuver_toggle = toggle_item(
      lambda: tr("Lateral Maneuver Mode"),
      description="",
      initial_state=self._params.get_bool("LateralManeuverMode"),
      callback=self._on_lat_maneuver_mode,
    )

    self._alpha_long_toggle = toggle_item(
      lambda: tr("sunnypilot Longitudinal Control (Alpha)"),
      description=lambda: tr(DESCRIPTIONS["alpha_longitudinal"]),
      initial_state=self._params.get_bool("AlphaLongitudinalEnabled"),
      callback=self._on_alpha_long_enabled,
      enabled=lambda: not ui_state.engaged,
    )

    self._ui_debug_toggle = toggle_item(
      lambda: tr("UI Debug Mode"),
      description="",
      initial_state=self._params.get_bool("ShowDebugInfo"),
      callback=self._on_enable_ui_debug,
    )
    self._on_enable_ui_debug(self._params.get_bool("ShowDebugInfo"))

    self._scroller = Scroller([
      self._adb_toggle,
      self._ssh_toggle,
      self._ssh_keys,
      self._bridge_toggle,
      self._fork_btn,
      self._joystick_toggle,
      self._long_maneuver_toggle,
      self._lat_maneuver_toggle,
      self._alpha_long_toggle,
      self._ui_debug_toggle,
    ], line_separator=True, spacing=0)

    # Toggles should be not available to change in onroad state
    ui_state.add_offroad_transition_callback(self._update_toggles)

  def _render(self, rect):
    self._scroller.render(rect)

  def show_event(self):
    super().show_event()
    self._scroller.show_event()
    self._update_toggles()

  def _update_toggles(self):
    ui_state.update_params()

    # Hide non-release toggles on release builds
    # TODO: we can do an onroad cycle, but alpha long toggle requires a deinit function to re-enable radar and not fault
    for item in (self._joystick_toggle, self._long_maneuver_toggle, self._lat_maneuver_toggle, self._alpha_long_toggle):
      item.set_visible(not self._is_release)

    # CP gating
    if ui_state.CP is not None:
      alpha_avail = ui_state.CP.alphaLongitudinalAvailable
      if not alpha_avail or self._is_release:
        self._alpha_long_toggle.set_visible(False)
        self._params.remove("AlphaLongitudinalEnabled")
      else:
        self._alpha_long_toggle.set_visible(True)

      long_man_enabled = ui_state.has_longitudinal_control and ui_state.is_offroad()
      self._long_maneuver_toggle.action_item.set_enabled(long_man_enabled)
      if not long_man_enabled:
        self._long_maneuver_toggle.action_item.set_state(False)
        self._params.put_bool("LongitudinalManeuverMode", False)

      lat_man_enabled = ui_state.is_offroad()
      self._lat_maneuver_toggle.action_item.set_enabled(lat_man_enabled)
    else:
      self._long_maneuver_toggle.action_item.set_enabled(False)
      self._lat_maneuver_toggle.action_item.set_enabled(False)
      self._alpha_long_toggle.set_visible(False)

    # TODO: make a param control list item so we don't need to manage internal state as much here
    # refresh toggles from params to mirror external changes
    for key, item in (
      ("AdbEnabled", self._adb_toggle),
      ("SshEnabled", self._ssh_toggle),
      ("BridgeEnabled", self._bridge_toggle),
      ("JoystickDebugMode", self._joystick_toggle),
      ("LongitudinalManeuverMode", self._long_maneuver_toggle),
      ("LateralManeuverMode", self._lat_maneuver_toggle),
      ("AlphaLongitudinalEnabled", self._alpha_long_toggle),
      ("ShowDebugInfo", self._ui_debug_toggle),
    ):
      item.action_item.set_state(self._params.get_bool(key))

  def _on_enable_ui_debug(self, state: bool):
    self._params.put_bool("ShowDebugInfo", state)
    gui_app.set_show_touches(state)
    gui_app.set_show_fps(state)
    gui_app.set_show_mouse_coords(state)

  def _on_enable_adb(self, state: bool):
    self._params.put_bool("AdbEnabled", state)

  def _on_enable_ssh(self, state: bool):
    self._params.put_bool("SshEnabled", state)

  def _on_enable_bridge(self, state: bool):
    self._params.put_bool("BridgeEnabled", state)

  def _load_forks(self):
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
            })
    except Exception:
      pass
    return forks

  def _get_current_fork_display(self):
    try:
      target = os.readlink("/data/openpilot")
      repo_dir = os.path.basename(target).replace("_", "/")
      branch = subprocess.check_output(
        ["git", "-C", target, "branch", "--show-current"],
        stderr=subprocess.DEVNULL, timeout=5,
      ).decode().strip()
      return f"{repo_dir}:{branch}" if branch else repo_dir
    except Exception:
      return "unknown"

  def _get_current_fork_option(self):
    display = self._get_current_fork_display()
    for fork in self._fork_list:
      if fork["display"] == display:
        return f"#{fork['key']} {fork['display']}"
    return ""

  def _on_select_fork(self):
    options = [f"#{f['key']} {f['display']}" for f in self._fork_list]
    current = self._get_current_fork_option()

    def handle_selection(result: DialogResult):
      if result == DialogResult.CONFIRM and self._fork_dialog is not None:
        selection = self._fork_dialog.selection
        if selection:
          key = selection.split(" ")[0].lstrip("#")
          display = selection.split(" ", 1)[1]

          def confirm_switch(result2: DialogResult):
            if result2 == DialogResult.CONFIRM:
              self._fork_btn.action_item.set_value(display)
              subprocess.Popen(
                ["bash", "/data/openpilot/tools/op.sh", "fork", key],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
              )

          dlg = ConfirmDialog(
            f"<h1>{tr('Switch Fork')}</h1><br><p>{tr('Switch to')} {display}? {tr('Device will reboot.')}</p>",
            tr("Switch"), callback=confirm_switch, rich=True,
          )
          gui_app.push_widget(dlg)
      self._fork_dialog = None

    self._fork_dialog = MultiOptionDialog(tr("Select a Fork"), options, current, callback=handle_selection)
    gui_app.push_widget(self._fork_dialog)

  def _on_joystick_debug_mode(self, state: bool):
    self._params.put_bool("JoystickDebugMode", state)
    self._params.put_bool("LongitudinalManeuverMode", False)
    self._long_maneuver_toggle.action_item.set_state(False)
    self._params.put_bool("LateralManeuverMode", False)
    self._lat_maneuver_toggle.action_item.set_state(False)

  def _on_long_maneuver_mode(self, state: bool):
    self._params.put_bool("LongitudinalManeuverMode", state)
    self._params.put_bool("JoystickDebugMode", False)
    self._joystick_toggle.action_item.set_state(False)
    self._params.put_bool("LateralManeuverMode", False)
    self._lat_maneuver_toggle.action_item.set_state(False)

  def _on_lat_maneuver_mode(self, state: bool):
    self._params.put_bool("LateralManeuverMode", state)
    self._params.put_bool("ExperimentalMode", False)
    self._params.put_bool("JoystickDebugMode", False)
    self._joystick_toggle.action_item.set_state(False)
    self._params.put_bool("LongitudinalManeuverMode", False)
    self._long_maneuver_toggle.action_item.set_state(False)

  def _on_alpha_long_enabled(self, state: bool):
    if state:
      def confirm_callback(result: DialogResult):
        if result == DialogResult.CONFIRM:
          self._params.put_bool("AlphaLongitudinalEnabled", True)
          self._params.put_bool("OnroadCycleRequested", True)
          self._update_toggles()
        else:
          self._alpha_long_toggle.action_item.set_state(False)

      # show confirmation dialog
      content = (f"<h1>{self._alpha_long_toggle.title}</h1><br>" +
                 f"<p>{self._alpha_long_toggle.description}</p>")

      dlg = ConfirmDialog(content, tr("Enable"), rich=True, callback=confirm_callback)
      gui_app.push_widget(dlg)

    else:
      self._params.put_bool("AlphaLongitudinalEnabled", False)
      self._params.put_bool("OnroadCycleRequested", True)
      self._update_toggles()
