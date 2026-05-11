> **Fork notice:** This repository is a fork of [sunnyhaibin/sunnypilot](https://github.com/sunnyhaibin/sunnypilot), which is a fork of [commaai/openpilot](https://github.com/commaai/openpilot). Built for the purpose of adding **Tesla Hardware 1** support to sunnypilot. The HW1 work is based on [xnor](https://github.com/xnor-tech/openpilot), which is itself based on [Tinkla (Unity)](https://github.com/BogGyver/openpilot).

## Tesla Documentation

| File | Purpose |
|------|---------|
| [`imports_to_maintain.md`](https://github.com/P6g9YHK6/opendbc/blob/master/opendbc/car/tesla/imports_to_maintain.md) | Tracks all HW1 changes from xnor-tech/StarPilot that must be preserved across upstream merges, with diff commands and merge checklist |
| [`todo_HW1.md`](https://github.com/P6g9YHK6/opendbc/blob/master/opendbc/car/tesla/todo_HW1.md) | Comprehensive improvement TODO list for Tesla HW1 (Model S/X 2014-16) covering missing signals, safety, longitudinal/lateral control, UI, and more |

## Installation

### Setup SSH

1. Generate an SSH key on your computer: `ssh-keygen -t ed25519`
2. Add the public key to your GitHub account (Settings > SSH and GPG keys)
3. On the comma device, go to **Settings > Developer > SSH Keys** and add your public key

### Prerequisites

- **Device:** comma 3 or comma 4 (same as upstream). Tested on comma 4 — feedback from other versions welcome.
- **Harness:** [xnor harness](https://xnor.shop) — required for connecting the comma device to the Tesla HW1 CAN bus.
- **Vehicle:** Tesla HW1 (Model S 2015 tested — feedback from other HW1 variants welcome)

### Install

SSH into the device and run:

```bash
cd /data && rm -rf openpilot
git clone --depth 1 --shallow-submodules --recurse-submodules -b master https://github.com/P6g9YHK6/SunnyPilot-TeslaHW1.git openpilot
cd openpilot
op setup
op build
sudo reboot
```

Feedback on the installation process is welcomed.


