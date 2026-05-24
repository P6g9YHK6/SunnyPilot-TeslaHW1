import os
import subprocess

from openpilot.common.time_helpers import system_time_valid
from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, BigToggle, BigParamControl, BigCircleParamControl
from openpilot.selfdrive.ui.mici.widgets.dialog import BigDialog, BigInputDialog
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
from openpilot.selfdrive.ui.layouts.settings.common import restart_needed_callback
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.widgets.ssh_key import SshKeyFetcher


class DeveloperLayoutMici(NavScroller):
  def __init__(self):
    super().__init__()
    self._ssh_fetcher = SshKeyFetcher(ui_state.params)

    def github_username_callback(username: str):
      if username:
        self._ssh_keys_btn.set_value("Loading...")
        self._ssh_keys_btn.set_enabled(False)

        def on_response(error):
          self._ssh_keys_btn.set_enabled(True)
          if error is None:
            self._ssh_keys_btn.set_value(username)
          else:
            self._ssh_keys_btn.set_value("Not set")
            gui_app.push_widget(BigDialog("", error))

        self._ssh_fetcher.fetch(username, on_response)
      else:
        self._ssh_fetcher.clear()
        self._ssh_keys_btn.set_value("Not set")

    def ssh_keys_callback():
      github_username = ui_state.params.get("GithubUsername") or ""
      dlg = BigInputDialog("enter GitHub username...", github_username, minimum_length=0, confirm_callback=github_username_callback)
      if not system_time_valid():
        dlg = BigDialog("", "Please connect to Wi-Fi to fetch your key.")
        gui_app.push_widget(dlg)
        return
      gui_app.push_widget(dlg)

    txt_ssh = gui_app.texture("icons_mici/settings/developer/ssh.png", 56, 64)
    github_username = ui_state.params.get("GithubUsername") or ""
    self._ssh_keys_btn = BigButton("SSH keys", "Not set" if not github_username else github_username, icon=txt_ssh)
    self._ssh_keys_btn.set_click_callback(ssh_keys_callback)

    # Load fork list from config
    self._fork_list = self._load_forks()

    # Fork switch button
    self._fork_btn = BigButton("Fork", self._get_current_fork_display())
    self._fork_btn.set_click_callback(self._on_select_fork)

    # adb, ssh, ssh keys, bridge, fork, debug mode, joystick debug mode, longitudinal maneuver mode, ip address
    # ******** Main Scroller ********
    self._adb_toggle = BigCircleParamControl(gui_app.texture("icons_mici/adb_short.png", 82, 82), "AdbEnabled", icon_offset=(0, 12))
    self._ssh_toggle = BigCircleParamControl(gui_app.texture("icons_mici/ssh_short.png", 82, 82), "SshEnabled", icon_offset=(0, 12))
    self._bridge_toggle = BigToggle("zmq bridge",
                                    initial_state=ui_state.params.get_bool("BridgeEnabled"),
                                    toggle_callback=self._on_enable_bridge)
    self._joystick_toggle = BigToggle("joystick debug mode",
                                      initial_state=ui_state.params.get_bool("JoystickDebugMode"),
                                      toggle_callback=self._on_joystick_debug_mode)
    self._long_maneuver_toggle = BigToggle("longitudinal maneuver mode",
                                           initial_state=ui_state.params.get_bool("LongitudinalManeuverMode"),
                                           toggle_callback=self._on_long_maneuver_mode)
    self._lat_maneuver_toggle = BigToggle("lateral maneuver mode",
                                          initial_state=ui_state.params.get_bool("LateralManeuverMode"),
                                          toggle_callback=self._on_lat_maneuver_mode)
    self._alpha_long_toggle = BigToggle("alpha longitudinal",
                                        initial_state=ui_state.params.get_bool("AlphaLongitudinalEnabled"),
                                        toggle_callback=self._on_alpha_long_enabled)
    self._debug_mode_toggle = BigParamControl("ui debug mode", "ShowDebugInfo",
                                              toggle_callback=lambda checked: (gui_app.set_show_touches(checked),
                                                                               gui_app.set_show_fps(checked)))

    self._scroller.add_widgets([
      self._adb_toggle,
      self._ssh_toggle,
      self._ssh_keys_btn,
      self._bridge_toggle,
      self._fork_btn,
      self._joystick_toggle,
      self._long_maneuver_toggle,
      self._lat_maneuver_toggle,
      self._alpha_long_toggle,
      self._debug_mode_toggle,
    ])

    # Toggle lists
    self._refresh_toggles = (
      ("AdbEnabled", self._adb_toggle),
      ("SshEnabled", self._ssh_toggle),
      ("BridgeEnabled", self._bridge_toggle),
      ("JoystickDebugMode", self._joystick_toggle),
      ("LongitudinalManeuverMode", self._long_maneuver_toggle),
      ("LateralManeuverMode", self._lat_maneuver_toggle),
      ("AlphaLongitudinalEnabled", self._alpha_long_toggle),
      ("ShowDebugInfo", self._debug_mode_toggle),
    )
    onroad_blocked_toggles = (self._adb_toggle, self._joystick_toggle)
    release_blocked_toggles = (self._joystick_toggle, self._long_maneuver_toggle, self._lat_maneuver_toggle, self._alpha_long_toggle)
    engaged_blocked_toggles = (self._long_maneuver_toggle, self._lat_maneuver_toggle, self._alpha_long_toggle)

    # Hide non-release toggles on release builds
    for item in release_blocked_toggles:
      item.set_visible(not ui_state.is_release)

    # Disable toggles that require offroad
    for item in onroad_blocked_toggles:
      item.set_enabled(lambda: ui_state.is_offroad())

    # Disable toggles that require not engaged
    for item in engaged_blocked_toggles:
      item.set_enabled(lambda: not ui_state.engaged)

    # Set initial state
    if ui_state.params.get_bool("ShowDebugInfo"):
      gui_app.set_show_touches(True)
      gui_app.set_show_fps(True)

    ui_state.add_offroad_transition_callback(self._update_toggles)

  def _update_state(self):
    super()._update_state()
    self._ssh_fetcher.update()

  def show_event(self):
    super().show_event()
    self._fork_btn.set_value(self._get_current_fork_display())
    self._update_toggles()

  def _update_toggles(self):
    ui_state.update_params()

    # CP gating
    if ui_state.CP is not None:
      alpha_avail = ui_state.CP.alphaLongitudinalAvailable
      if not alpha_avail or ui_state.is_release:
        self._alpha_long_toggle.set_visible(False)
        ui_state.params.remove("AlphaLongitudinalEnabled")
      else:
        self._alpha_long_toggle.set_visible(True)

      long_man_enabled = ui_state.has_longitudinal_control and ui_state.is_offroad()
      self._long_maneuver_toggle.set_enabled(long_man_enabled)
      if not long_man_enabled:
        self._long_maneuver_toggle.set_checked(False)
        ui_state.params.put_bool("LongitudinalManeuverMode", False)

      lat_man_enabled = ui_state.is_offroad()
      self._lat_maneuver_toggle.set_enabled(lat_man_enabled)
    else:
      self._long_maneuver_toggle.set_enabled(False)
      self._lat_maneuver_toggle.set_enabled(False)
      self._alpha_long_toggle.set_visible(False)

    # Refresh toggles from params to mirror external changes
    for key, item in self._refresh_toggles:
      item.set_checked(ui_state.params.get_bool(key))

  def _on_joystick_debug_mode(self, state: bool):
    ui_state.params.put_bool("JoystickDebugMode", state)
    ui_state.params.put_bool("LongitudinalManeuverMode", False)
    self._long_maneuver_toggle.set_checked(False)
    ui_state.params.put_bool("LateralManeuverMode", False)
    self._lat_maneuver_toggle.set_checked(False)

  def _on_long_maneuver_mode(self, state: bool):
    ui_state.params.put_bool("LongitudinalManeuverMode", state)
    ui_state.params.put_bool("JoystickDebugMode", False)
    self._joystick_toggle.set_checked(False)
    ui_state.params.put_bool("LateralManeuverMode", False)
    self._lat_maneuver_toggle.set_checked(False)
    restart_needed_callback(state)

  def _on_lat_maneuver_mode(self, state: bool):
    ui_state.params.put_bool("LateralManeuverMode", state)
    ui_state.params.put_bool("ExperimentalMode", False)
    ui_state.params.put_bool("JoystickDebugMode", False)
    self._joystick_toggle.set_checked(False)
    ui_state.params.put_bool("LongitudinalManeuverMode", False)
    self._long_maneuver_toggle.set_checked(False)
    restart_needed_callback(state)

  def _on_alpha_long_enabled(self, state: bool):
    # TODO: show confirmation dialog before enabling
    ui_state.params.put_bool("AlphaLongitudinalEnabled", state)
    restart_needed_callback(state)
    self._update_toggles()

  def _on_enable_bridge(self, state: bool):
    ui_state.params.put_bool("BridgeEnabled", state)

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

    def handle_selection(result):
      if result == DialogResult.CONFIRM and self._fork_dialog is not None:
        selection = self._fork_dialog.selection
        if selection:
          key = selection.split(" ")[0].lstrip("#")
          display = selection.split(" ", 1)[1]

          def confirm_switch(result2):
            if result2 == DialogResult.CONFIRM:
              self._fork_btn.set_value(display)
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
