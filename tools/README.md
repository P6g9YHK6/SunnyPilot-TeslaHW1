# openpilot tools

## System Requirements

openpilot is developed and tested on **Ubuntu 24.04**, which is the primary development target aside from the [supported embedded hardware](https://github.com/commaai/openpilot#running-on-a-dedicated-device-in-a-car).

Most of openpilot should work natively on macOS. On Windows you can use WSL for a nearly native Ubuntu experience. Running natively on any other system is not currently recommended and will likely require modifications.

## Native setup on Ubuntu 24.04 and macOS

Follow these instructions for a fully managed setup experience. If you'd like to manage the dependencies yourself, just read the setup scripts in this directory.

**1. Clone openpilot**
``` bash
git clone https://github.com/commaai/openpilot.git
```

**2. Run the setup script**
``` bash
cd openpilot
tools/op.sh setup
```

**3. Activate a Python shell**
Activate a shell with the Python dependencies installed:
``` bash
source .venv/bin/activate
```

**4. Build openpilot**
``` bash
scons -u -j$(nproc)
```

## WSL on Windows

[Windows Subsystem for Linux (WSL)](https://docs.microsoft.com/en-us/windows/wsl/about) should provide a similar experience to native Ubuntu. [WSL 2](https://docs.microsoft.com/en-us/windows/wsl/compare-versions) specifically has been reported by several users to be a seamless experience.

Follow [these instructions](https://docs.microsoft.com/en-us/windows/wsl/install) to setup the WSL and install the `Ubuntu-24.04` distribution. Once your Ubuntu WSL environment is setup, follow the Linux setup instructions to finish setting up your environment. See [these instructions](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps) for running GUI apps.

**NOTE**: If you are running WSL 2 and experiencing performance issues with the UI or simulator, you may need to explicitly enable hardware acceleration by setting `GALLIUM_DRIVER=d3d12` before commands. Add `export GALLIUM_DRIVER=d3d12` to your `~/.bashrc` file to make it automatic for future sessions.

## CTF
Learn about the openpilot ecosystem and tools by playing our [CTF](/tools/CTF.md).

## op fork — Multi-Fork Manager

`op fork` manages multiple openpilot forks on a comma device. All clones live under `/data/forks/` with one clone per repository — `git checkout` switches between branches of the same repo. `/data/openpilot` is a symlink pointing to the active fork.

Forks are defined in `tools/forks.conf`:

```
<number> <user/repo> <branch> [comment]
```

| Field     | Description                          | Example                  |
|-----------|--------------------------------------|--------------------------|
| `number`  | Index used to select this fork       | `1`                      |
| `user/repo` | GitHub repository                 | `sunnypilot/sunnypilot`  |
| `branch`  | Remote branch to track               | `dev`                    |
| `comment` | Optional label (e.g. target device)  | `C4`                     |

```
op fork                   Interactive menu (or run any action directly)
op fork list              List all forks with ahead/behind status
op fork <N|UN>            Switch to fork (clone → checkout → symlink → OS update → reboot)
op fork update <N|UN|all> Update fork(s) (fetch + merge --ff-only)
op fork info <N|UN>       Show SHA, date, commit title, ahead/behind
op fork purge <N|UN>      Purge fork
op fork help              Show usage
```

`op fork list` shows ahead/behind counts (e.g. `↑3 ↓1`) instead of a boolean update flag. `op fork update all` iterates all downloaded declared and untracked forks.

Untracked forks (clones under `/data/forks/` not in `forks.conf`) appear in the list as `[U1]`, `[U2]`, etc. with an `(untracked)` marker, and support the same update/purge/switch operations.

### First Setup

If `/data/openpilot` is a real directory (e.g. from a README install), the first `op fork <N>` automatically migrates it into `/data/forks/`, converts `/data/openpilot` to a symlink, and switches to the selected fork. No data loss.

### AGNOS Updates

If the AGNOS version required by the fork differs from the installed version, `op fork <N>` runs the OS update automatically before rebooting.

## Directory Structure

```
├── cabana/             # View and plot CAN messages from drives or in realtime
├── camerastream/       # Cameras stream over the network
├── forks.conf          # Fork definitions for `op fork`
├── joystick/           # Control your car with a joystick
├── lib/                # Libraries to support the tools and reading openpilot logs
├── plotjuggler/        # A tool to plot openpilot logs
├── replay/             # Replay drives and mock openpilot services
├── scripts/            # Miscellaneous scripts
├── serial/             # Tools for using the comma serial
├── sim/                # Run openpilot in a simulator
└── webcam/             # Run openpilot on a PC with webcams
```
