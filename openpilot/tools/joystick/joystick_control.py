#!/usr/bin/env python3
import os
import argparse
import math
import threading
import time
import numpy as np
from inputs import UnpluggedError, get_gamepad, devices as input_devices, DeviceManager

from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.realtime import Ratekeeper
from openpilot.common.hardware import HARDWARE
from openpilot.tools.lib.kbhit import KBHit

EXPO = 0.7
STEER_DEADZONE = 0.02


class Keyboard:
  def __init__(self):
    self.kb = KBHit()
    self.axis_increment = 0.05  # 5% of full actuation each key press
    self.axes_map = {'w': 'gb', 's': 'gb',
                     'a': 'steer', 'd': 'steer'}
    self.axes_values = {'gb': 0., 'steer': 0.}
    self.axes_order = ['gb', 'steer']
    self.cancel = False

  def update(self):
    key = self.kb.getch().lower()
    self.cancel = False
    if key == 'r':
      self.axes_values = dict.fromkeys(self.axes_values, 0.)
    elif key == 'c':
      self.cancel = True
    elif key in self.axes_map:
      axis = self.axes_map[key]
      incr = self.axis_increment if key in ['w', 'a'] else -self.axis_increment
      self.axes_values[axis] = float(np.clip(self.axes_values[axis] + incr, -1, 1))
    else:
      return False
    return True


class Joystick:
  def __init__(self):
    self.cancel_button = 'BTN_NORTH'
    self._last_rescan = 0.0
    self._detect_mapping()

  def _detect_mapping(self):
    _name = ''
    if input_devices.gamepads:
      try:
        _name = input_devices.gamepads[0].name
      except Exception:
        pass

    if HARDWARE.get_device_type() == 'pc':
      accel_axis = 'ABS_Z'
      steer_axis = 'ABS_RX'
      flip_map = {'ABS_RZ': accel_axis}
      accel_range = (0., 255.)
      steer_range = (0., 255.)
    elif 'Xbox' in _name or 'X-Box' in _name:
      accel_axis = 'ABS_Z'
      steer_axis = 'ABS_RX'
      flip_map = {'ABS_RZ': accel_axis}
      accel_range = (-255., 255.)
      steer_range = (-32768., 32767.)
    else:
      accel_axis = 'ABS_RX'
      steer_axis = 'ABS_Z'
      flip_map = {'ABS_RY': accel_axis}
      accel_range = (0., 255.)
      steer_range = (0., 255.)

    self.flip_map = flip_map
    self.min_axis_value = {accel_axis: accel_range[0], steer_axis: steer_range[0]}
    self.max_axis_value = {accel_axis: accel_range[1], steer_axis: steer_range[1]}
    self.axes_order = [accel_axis, steer_axis]

    new_values = {}
    for ax in self.axes_order:
      new_values[ax] = getattr(self, 'axes_values', {}).get(ax, 0.)
    self.axes_values = new_values

  def update(self):
    try:
      joystick_event = get_gamepad()[0]
    except (OSError, UnpluggedError):
      self.axes_values = dict.fromkeys(self.axes_values, 0.)
      now = time.monotonic()
      if now - self._last_rescan > 2.0:
        try:
          dm = DeviceManager()
          if dm.gamepads:
            input_devices.gamepads[:] = dm.gamepads
            self._detect_mapping()
        except Exception:
          pass
        self._last_rescan = now
      return False

    event = (joystick_event.code, joystick_event.state)

    # flip left trigger to negative accel
    if event[0] in self.flip_map:
      event = (self.flip_map[event[0]], -event[1])

    if event[0] == self.cancel_button:
      if event[1] == 1:
        self.cancel = True
      elif event[1] == 0:   # state 0 is falling edge
        self.cancel = False
    elif event[0] in self.axes_values:
      self.max_axis_value[event[0]] = max(event[1], self.max_axis_value[event[0]])
      self.min_axis_value[event[0]] = min(event[1], self.min_axis_value[event[0]])

      norm = -float(np.interp(event[1], [self.min_axis_value[event[0]], self.max_axis_value[event[0]]], [-1., 1.]))
      deadzone = STEER_DEADZONE if event[0] == self.axes_order[1] else 0.10
      norm = norm if abs(norm) > deadzone else 0.
      steer_exp = 4 if event[0] == self.axes_order[1] else 3
      self.axes_values[event[0]] = EXPO * math.copysign(abs(norm) ** steer_exp, norm) + (1 - EXPO) * norm
    else:
      return False
    return True


def send_thread(joystick):
  pm = messaging.PubMaster(['testJoystick'])

  rk = Ratekeeper(100, print_delay_threshold=None)

  while True:
    if rk.frame % 20 == 0:
      print('\n' + ', '.join(f'{name}: {round(v, 3)}' for name, v in joystick.axes_values.items()))

    joystick_msg = messaging.new_message('testJoystick')
    joystick_msg.valid = True
    joystick_msg.testJoystick.axes = [joystick.axes_values[ax] for ax in joystick.axes_order]

    pm.send('testJoystick', joystick_msg)

    rk.keep_time()


def joystick_control_thread(joystick):
  Params().put_bool('JoystickDebugMode', True, block=True)
  threading.Thread(target=send_thread, args=(joystick,), daemon=True).start()
  while True:
    joystick.update()


def main():
  joystick_control_thread(Joystick())


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Publishes events from your joystick to control your car.\n' +
                                               'openpilot must be offroad before starting joystick_control. This tool supports ' +
                                               'a PlayStation 5 DualSense controller on the comma 3X.',
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument('--keyboard', action='store_true', help='Use your keyboard instead of a joystick')
  args = parser.parse_args()

  if not Params().get_bool("IsOffroad") and "ZMQ" not in os.environ:
    print("The car must be off before running joystick_control.")
    exit()

  print()
  if args.keyboard:
    print('Gas/brake control: `W` and `S` keys')
    print('Steering control: `A` and `D` keys')
    print('Buttons')
    print('- `R`: Resets axes')
    print('- `C`: Cancel cruise control')
  else:
    print('Using joystick, make sure to run openpilot/cereal/messaging/bridge on your device if running over the network!')
    print('If not running on a comma device, the mapping may need to be adjusted.')

  joystick = Keyboard() if args.keyboard else Joystick()
  joystick_control_thread(joystick)
