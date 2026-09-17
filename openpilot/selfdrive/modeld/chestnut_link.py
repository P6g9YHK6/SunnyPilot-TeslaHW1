"""Raw-USB probing of the chestnut ASM2464 bridge, used by modeld.py to decide
whether to attempt the big/chestnut model *before* any cereal message exists and
*before* tinygrad's Device["AMD"] is ever opened.

History (see git log -- modeld.py): a104000db added an independent hardwared-side
chestnutState publisher; 2cd7be57b added modeld's wait-loop on that topic ("wait
for stable chestnut") - correct *given* a104000db's publisher. 59a182332 reverted
ONLY a104000db, stranding the wait-loop: nothing publishes chestnutState before
modeld's own (post-wait) ChestnutState.send() ever runs, so the wait always times
out and CHESTNUT is permanently False.

This module fixes that without a second publisher on 'chestnutState' (would risk
MultiplePublishersError against ChestnutState.send()) - it talks to the hardware
directly, in-process, once at startup. Only modeld touches chestnut hardware (see
ChestnutState's own "only modeld can access chestnut" comment) - this preserves
that invariant.
"""
import struct
import time

import usb1

from openpilot.common.hardware.usb import CHESTNUT_USB_IDS, CHESTNUT_PCIE_READY
from openpilot.system.hardware.chestnut.flash import link_up
from openpilot.selfdrive.modeld.helpers import chestnut_ready

PROBE_TIMEOUT_S = 3.0
PROBE_INTERVAL_S = 0.2
STABLE_READS = 3


class ChestnutUsb:
  """Pre-bootstrap-only USB-INA reader. Mirrors ChestnutState._open_asm_usb/_read_ina's
  raw usb1 fallback path in modeld.py - the Device["AMD"]-backed fast path there
  doesn't exist yet at this point in startup, by construction."""
  def __init__(self):
    self._handle = None

  def close(self) -> None:
    if self._handle is not None:
      try:
        self._handle.close()
      except Exception:
        pass
      self._handle = None

  def _connect(self):
    context = usb1.USBContext()
    for vendor_id, product_id in CHESTNUT_USB_IDS:
      if (handle := context.openByVendorIDAndProductID(vendor_id, product_id, skip_on_error=True)) is not None:
        return handle
    context.close()
    return None

  def read_ina(self) -> tuple[int, int, bool]:
    if self._handle is None:
      self._handle = self._connect()
    if self._handle is None:
      raise usb1.USBErrorNoDevice
    try:
      raw = self._handle.controlRead(0xC0, 0xC0, 0, 0, 5, timeout=100)
    except usb1.USBError:
      self.close()
      raise
    return struct.unpack('<Hh?', bytes(raw))


class _Reading:
  """Duck-types the fields chestnut_ready() reads off a real chestnutState capnp reader."""
  def __init__(self, supplyVoltage: int, supplyCurrent: int, supplyFault: bool, pcieLtssm: int):
    self.supplyVoltage = supplyVoltage
    self.supplyCurrent = supplyCurrent
    self.supplyFault = supplyFault
    self.pcieLtssm = pcieLtssm


def wait_for_stable_chestnut(timeout: float = PROBE_TIMEOUT_S, interval: float = PROBE_INTERVAL_S,
                              stable_reads: int = STABLE_READS) -> bool:
  """Polls real hardware directly (no cereal) until chestnut_ready() holds for
  `stable_reads` consecutive samples, or `timeout` elapses. Any read exception
  (device momentarily gone, USB hiccup) resets the streak rather than raising -
  this is a best-effort readiness gate, not a hard hardware assertion."""
  asm = ChestnutUsb()
  consecutive = 0
  deadline = time.monotonic() + timeout
  try:
    while time.monotonic() < deadline:
      try:
        pcie_ready = link_up()
        voltage, current, fault = asm.read_ina()
      except Exception:
        consecutive = 0
      else:
        reading = _Reading(voltage, current, fault, CHESTNUT_PCIE_READY if pcie_ready else 0x00)
        consecutive = consecutive + 1 if chestnut_ready(reading) else 0
        if consecutive >= stable_reads:
          return True
      time.sleep(interval)
  finally:
    asm.close()
  return False
