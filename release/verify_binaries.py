#!/usr/bin/env python3
"""
Fails the build if any NativeProcess binary declared in process_config.py is
missing from the build output. Run after `scons` and before packaging/publishing
a release, so a build that silently drops a required binary (wrong SConscript
gating, missed arch, etc.) never reaches a device.
"""
import builtins
import io
import os
import sys

# process_config.py transitively imports calibrationd.py, which reads this
# devicetree path at MODULE level (not inside a function) to detect the
# device type. It only ever exists on real hardware; this CI runner has no
# devicetree at all. Neutralize just this one path rather than importing
# a fake filesystem or touching the source - manager.py itself never hits
# this on a real device, so the check is meaningless here anyway.
_DEVICETREE_MODEL_PATH = "/sys/firmware/devicetree/base/model"
_real_open = builtins.open


def _open_with_devicetree_stub(path, *args, **kwargs):
  if str(path) == _DEVICETREE_MODEL_PATH:
    return io.StringIO("comma mici\x00")
  return _real_open(path, *args, **kwargs)


builtins.open = _open_with_devicetree_stub
try:
  from openpilot.system.manager.process_config import managed_processes
  from openpilot.system.manager.process import NativeProcess
finally:
  builtins.open = _real_open

# these run a script/interpreter rather than a compiled binary as cmdline[0]
SCRIPT_INTERPRETERS = {"bash", "sh"}


def compiled_binary_path(proc: NativeProcess) -> str | None:
  exe = proc.cmdline[0]
  if exe in SCRIPT_INTERPRETERS:
    return None
  if exe.endswith((".py", ".sh")):
    return None
  return exe


def main() -> int:
  build_dir = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BUILD_DIR")
  if not build_dir:
    print("usage: verify_binaries.py <build_dir>  (or set $BUILD_DIR)", file=sys.stderr)
    return 1

  missing = []
  checked = []
  for proc in managed_processes.values():
    if not isinstance(proc, NativeProcess) or not proc.enabled:
      continue

    exe = compiled_binary_path(proc)
    if exe is None:
      continue

    path = os.path.normpath(os.path.join(build_dir, proc.cwd, exe))
    checked.append(path)
    if not (os.path.isfile(path) and os.access(path, os.X_OK)):
      missing.append((proc.name, path))

  print(f"[verify_binaries] checked {len(checked)} expected native binaries under {build_dir}")

  if missing:
    print("\n[verify_binaries] BUILD IS MISSING REQUIRED BINARIES:", file=sys.stderr)
    for name, path in missing:
      print(f"  - {name}: expected at {path}", file=sys.stderr)
    print(
      "\nThis release would silently ship without these processes. "
      "Check the SConstruct/SConscript gating for the platform this was built for.",
      file=sys.stderr,
    )
    return 1

  print("[verify_binaries] all expected native binaries present.")
  return 0


if __name__ == "__main__":
  sys.exit(main())
