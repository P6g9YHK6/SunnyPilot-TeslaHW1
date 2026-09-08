import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

CHESTNUT_FW_VERSION = "ed4e39b7"
CHESTNUT_USB_IDS = ((0xADD1, 0x0001), (0x3801, 0x0001))
CHESTNUT_ROM_USB_IDS = ((0x174C, 0x2464), (0x174C, 0x2463))
CHESTNUT_USB_PRODUCT = f"custom {CHESTNUT_FW_VERSION}-CLEAN"
USB_DEVICES_PATH = Path("/sys/bus/usb/devices")
TYPEC_CC_ORIENTATION_PATH = Path("/sys/class/power_supply/usb/typec_cc_orientation")
PRIMARY_USB_CONTROLLER = "a600000.ssusb"

# canonical home for chestnut readiness thresholds - previously triplicated (with
# slightly different literal spellings) across system/hardware/chestnut/status.py
# and selfdrive/modeld/helpers.py
CHESTNUT_POWERED_VOLTAGE = 5000  # mV
CHESTNUT_PCIE_READY = 0x78       # ChestnutState.pcieLtssm "link up"
CHESTNUT_SLOW_USB_MBPS = 5000    # USB 3.0 5 Gbps; below this the link negotiated down


def is_chestnut_usb_id(vendor_id: int, product_id: int, include_bootloader: bool = False) -> bool:
  ids = CHESTNUT_USB_IDS + CHESTNUT_ROM_USB_IDS if include_bootloader else CHESTNUT_USB_IDS
  return (vendor_id, product_id) in ids


def decode_pcie_ltssm(value: int) -> str:
  """Best-effort human label for ChestnutState.pcieLtssm. Only 0x78 ("link up") and
  0x00 ("down/detect") are backed by in-repo evidence - no ASM2464 LTSSM reference
  exists anywhere in this codebase, so every other value is deliberately left
  generic (with the raw hex still shown) rather than guessed at, the way an earlier
  ad hoc frontend table did (and got wrong - it never even included 0x78, the one
  value chestnut_ready() actually treats as meaningful)."""
  if value == CHESTNUT_PCIE_READY:
    return f"Link Up (0x{value:02x})"
  if value == 0x00:
    return f"Down / Not Linked (0x{value:02x})"
  return f"Training / Unknown (0x{value:02x})"


class ChestnutState(StrEnum):
  ABSENT = "absent"
  BOOTLOADER = "bootloader"
  FIRMWARE_MISMATCH = "firmware_mismatch"
  UNCOMPILED = "uncompiled"
  NOT_READY_POWER = "not_ready_power"
  NOT_READY_PCIE = "not_ready_pcie"
  NOT_READY = "not_ready"          # no telemetry yet, or both power+pcie bad
  DEGRADED_LINK = "degraded_link"  # ready, but USB link below CHESTNUT_SLOW_USB_MBPS
  READY = "ready"
  ACTIVE = "active"


CHESTNUT_STATE_LABELS: dict[ChestnutState, str] = {
  ChestnutState.ABSENT: "Not Detected",
  ChestnutState.BOOTLOADER: "Bootloader / Recovery Mode",
  ChestnutState.FIRMWARE_MISMATCH: "Firmware Mismatch",
  ChestnutState.UNCOMPILED: "Model Not Compiled",
  ChestnutState.NOT_READY_POWER: "Not Ready (Power)",
  ChestnutState.NOT_READY_PCIE: "Not Ready (PCIe)",
  ChestnutState.NOT_READY: "Not Ready",
  ChestnutState.DEGRADED_LINK: "Degraded USB Link",
  ChestnutState.READY: "Ready",
  ChestnutState.ACTIVE: "Active",
}


@dataclass
class ChestnutHardwareInfo:
  state: ChestnutState
  present: bool
  firmware_ok: bool
  pcie_link_up: bool | None
  powered: bool | None
  slow_usb: bool
  pcie_label: str


def get_chestnut_hardware_state(devices: list[dict], state, compiled: bool,
                                 active: bool = False) -> ChestnutHardwareInfo:
  """Single source of truth for "what state is chestnut in", covering the full
  lifecycle from not-plugged-in through actively-driving-the-model. `state` is a
  ChestnutState (cereal) reader (tempC/pcieLtssm/supplyVoltage/supplyFault attrs) or
  None if no message has ever been received; duck-typed on purpose so this module
  doesn't need a `cereal` import. `devices` is get_usb_state()'s own return shape
  (note: distinct from this module's own usb_devices() function, which returns
  sysfs Paths, not parsed dicts). `compiled` is
  selfdrive/modeld/helpers.py's chestnut_compiled()."""
  bootloader_only = any(is_chestnut_usb_id(d["vendorId"], d["productId"], include_bootloader=True)
                        and not is_chestnut_usb_id(d["vendorId"], d["productId"]) for d in devices)
  app_devices = [d for d in devices if is_chestnut_usb_id(d["vendorId"], d["productId"])]

  if not app_devices and not bootloader_only:
    return ChestnutHardwareInfo(ChestnutState.ABSENT, False, False, None, None, False, "—")
  if bootloader_only and not app_devices:
    return ChestnutHardwareInfo(ChestnutState.BOOTLOADER, True, False, None, None, False, "—")

  device = next((d for d in app_devices if d["speedMbps"]), app_devices[0])
  firmware_ok = len(app_devices) == 1 and device["product"] == CHESTNUT_USB_PRODUCT
  slow_usb = len(app_devices) == 1 and device["speedMbps"] < CHESTNUT_SLOW_USB_MBPS

  if not firmware_ok:
    return ChestnutHardwareInfo(ChestnutState.FIRMWARE_MISMATCH, True, False, None, None, slow_usb, "—")
  if not compiled:
    return ChestnutHardwareInfo(ChestnutState.UNCOMPILED, True, True, None, None, slow_usb, "—")
  if state is None:
    return ChestnutHardwareInfo(ChestnutState.NOT_READY, True, True, None, None, slow_usb, "—")

  pcie_link_up = int(state.pcieLtssm) == CHESTNUT_PCIE_READY
  powered = state.supplyVoltage >= CHESTNUT_POWERED_VOLTAGE and not state.supplyFault
  pcie_label = decode_pcie_ltssm(int(state.pcieLtssm))

  if not powered and not pcie_link_up:
    hw_state = ChestnutState.NOT_READY
  elif not powered:
    hw_state = ChestnutState.NOT_READY_POWER
  elif not pcie_link_up:
    hw_state = ChestnutState.NOT_READY_PCIE
  elif slow_usb:
    hw_state = ChestnutState.DEGRADED_LINK
  else:
    hw_state = ChestnutState.ACTIVE if active else ChestnutState.READY

  return ChestnutHardwareInfo(hw_state, True, True, pcie_link_up, powered, slow_usb, pcie_label)


def get_usb_topology() -> set[str]:
  try:
    return set(os.listdir(USB_DEVICES_PATH))
  except OSError:
    return set()


def read(path: Path) -> str | None:
  try:
    return path.read_text().strip()
  except OSError:
    return None


def read_int(path: Path, base: int = 10) -> int:
  try:
    return int(path.read_text(), base)
  except (OSError, ValueError, TypeError):
    return 0


def usb_devices() -> list[Path]:
  try:
    devices = (d for d in USB_DEVICES_PATH.glob("*") if (d / "idVendor").exists())
    return sorted(devices, key=lambda p: p.name)
  except OSError:
    return []


def controller(device: Path) -> Path | None:
  try:
    return next((parent for parent in device.resolve().parents if parent.name.endswith(".ssusb")), None)
  except OSError:
    return None


def get_usb_state() -> list[dict]:
  devices = []
  typec_orientation = read_int(TYPEC_CC_ORIENTATION_PATH)
  for device in usb_devices():
    vendor_id = read_int(device / "idVendor", 16)
    product_id = read_int(device / "idProduct", 16)
    ctrl = controller(device)
    devices.append({
      "busnum": read_int(device / "busnum"),
      "devnum": read_int(device / "devnum"),
      "vendorId": vendor_id,
      "productId": product_id,
      "speedMbps": read_int(device / "speed"),
      "manufacturer": read(device / "manufacturer") or "",
      "product": read(device / "product") or "",
      "linkErrorCount": read_int(ctrl / "portli", 0) & 0xFFFF if ctrl is not None else 0,
      "usb3Lane": {1: "a", 2: "b"}.get(typec_orientation, "unknown") if ctrl is not None and ctrl.name == PRIMARY_USB_CONTROLLER else "unknown",
    })
  return devices


def set_usb_state(device_state, devices: list[dict]) -> None:
  entries = device_state.usbState.init('devices', len(devices))

  chestnut_present = False
  for entry, device in zip(entries, devices, strict=True):
    entry.busnum = device["busnum"]
    entry.devnum = device["devnum"]
    entry.vendorId = device["vendorId"]
    entry.productId = device["productId"]
    entry.speedMbps = device["speedMbps"]
    entry.manufacturer = device["manufacturer"]
    entry.product = device["product"]
    entry.linkErrorCount = device["linkErrorCount"]
    entry.usb3Lane = device.get("usb3Lane", "unknown")

    if is_chestnut_usb_id(entry.vendorId, entry.productId):
      chestnut_present = True

  device_state.chestnutPresent = chestnut_present
