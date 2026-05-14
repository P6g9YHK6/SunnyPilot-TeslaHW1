> **Fork notice:** This repository is a fork of [sunnypilot/sunnypilot](https://github.com/sunnypilot/sunnypilot), which is a fork of [commaai/openpilot](https://github.com/commaai/openpilot). Built for the purpose of adding **Tesla Hardware 1** support to sunnypilot. The HW1/AP1 work is based on [xnor](https://github.com/xnor-tech/openpilot), is the successor of [Tinkla (Unity)](https://github.com/BogGyver/openpilot).
## Background
This project was initially meant to support StarPilot, but due to the time it took to swap between OS even with the new [`op fork`](tools/op.sh) tool, sunnypilot with its recent update [v2026.001.000](https://github.com/sunnypilot/sunnypilot/releases/tag/v2026.001.000) (2026-05-06) adding support for both comma 3 & 4 became an easy target for porting.
## Installation
### Prerequisites
- **Device:** comma 3 or comma 4 (same as upstream). Tested on comma 4 - feedback from other versions welcome.
- **Harness:** [xnor harness](https://xnor.shop) - required for connecting the comma device to the tesla CAN bus.
- **Vehicle:** Tesla HW1/AP1 (Model S 2015, Model X 2016 tested). HW2 may work, untested. Pre-AP unsupported until AP1/AP2 reach feature parity with other cars.
### Install
#### SSH
Generate an SSH key (`ssh-keygen -t ed25519`), add it to GitHub, then on the device go to **Settings > Developer > SSH Keys** and enter your GitHub username.

SSH into the device (`ssh comma@<device-ip>`) and run:
```bash
cd /data && rm -rf openpilot
git clone --depth 1 --shallow-submodules --recurse-submodules -b master https://github.com/P6g9YHK6/SunnyPilot-TeslaHW1.git openpilot
cd openpilot
op setup
op build -j2 2>&1 | tee /data/build.log
sudo reboot
```
Feedback on the installation process is welcomed. If AGNOS versions differ, `op fork <N>` updates the OS automatically before reboot. No `fork` after swap? Run `/data/forks/P6g9YHK6_SunnyPilot-TeslaHW1/tools/op.sh fork list`.

#### comma UI
When requested for a custom install URL, use:
```
P6g9YHK6/master
```
(untested)
## Upstream Updates
| Upstream | Branch | Last Commit |
|----------|--------|-------------|
| [sunnyhaibin/sunnypilot](https://github.com/sunnyhaibin/sunnypilot) | `master` | `78007e82e` (2026-05-11) |
| [sunnyhaibin/opendbc](https://github.com/sunnyhaibin/opendbc) | `master` | `4dad7b09` (2026-05-09) |
| [sunnyhaibin/panda](https://github.com/sunnyhaibin/panda) | `master` | `0a9ef7ab` (2026-04-26) |
| [xnor-tech/openpilot](https://github.com/xnor-tech/openpilot) | `xnor-dev` | `eae878da2` (2026-04-25) |
| [xnor-tech/opendbc](https://github.com/xnor-tech/opendbc) | `master-xnor` | `78039539` (2026-04-25) |
| [xnor-tech/panda](https://github.com/xnor-tech/panda) | `master-xnor` | `56920ec6` (2026-04-11) |
## Tesla Documentation
| File | Purpose |
|------|---------|
| [`imports_to_maintain.md`](https://github.com/P6g9YHK6/opendbc/blob/master/opendbc/car/tesla/imports_to_maintain.md) | Tracks all HW1 changes from xnor-tech/StarPilot that must be preserved across upstream merges, with diff commands and merge checklist |
| [`todo_HW1.md`](https://github.com/P6g9YHK6/opendbc/blob/master/opendbc/car/tesla/todo_HW1.md) | Comprehensive improvement TODO list for Tesla HW1 (AP1) (Model S/X 2014-16) covering missing signals, safety, longitudinal/lateral control, UI, and more |
## Roadmap
The following goals are in no particular order:
- [ ] Feature parity with other openpilot-supported cars
- [ ] HW2/AP2 support
- [ ] Pre-AP support
- [ ] Local web UI independent from SunnyLink
- [ ] Prototype replacement of Tesla app
## Other Documentation
- [commaai/openpilot wiki - Tesla](https://github.com/commaai/openpilot/wiki/Tesla) — Official commaai documentation on Tesla hardware compatibility, flashing, and general openpilot/Tesla usage. Useful reference for HW1/HW2 support setup and troubleshooting.
- [CARS.md](https://github.com/commaai/openpilot/blob/master/docs/CARS.md) — Official list of supported vehicles and their feature coverage in openpilot.
