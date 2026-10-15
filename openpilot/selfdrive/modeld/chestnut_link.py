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
from openpilot.selfdrive.modeld.helpers import chestnut_ready

PROBE_TIMEOUT_S = 3.0
PROBE_INTERVAL_S = 0.2
STABLE_READS = 3
LTSSM_REG = 0xB450


class ChestnutUsb:
  """Pre-bootstrap-only ASM2464 reader. Mirrors ChestnutState._open_asm_usb/_read_ina's
  raw usb1 fallback path in modeld.py - the Device["AMD"]-backed fast path there
  doesn't exist yet at this point in startup, by construction."""
  def __init__(self):
    self._context = None
    self._handle = None

  def close(self) -> None:
    for obj in (self._handle, self._context):
      if obj is not None:
        try:
          obj.close()
        except Exception:
          pass
    self._handle = self._context = None

  def _connect(self) -> None:
    self._context = usb1.USBContext()
    for vendor_id, product_id in CHESTNUT_USB_IDS:
      if (handle := self._context.openByVendorIDAndProductID(vendor_id, product_id, skip_on_error=True)) is not None:
        self._handle = handle
        return
    self.close()

  def _control_read(self, request: int, value: int, length: int) -> bytes:
    if self._handle is None:
      self._connect()
    if self._handle is None:
      raise usb1.USBErrorNoDevice
    try:
      return bytes(self._handle.controlRead(0xC0, request, value, 0, length, timeout=100))
    except usb1.USBError:
      self.close()
      raise

  def read_ina(self) -> tuple[int, int, bool]:
    return struct.unpack('<Hh?', self._control_read(0xC0, 0, 5))

  def read_ltssm(self) -> int:
    return self._control_read(0xE4, LTSSM_REG, 1)[0]

  def power_on_pcie(self) -> None:
    # tinygrad's CustomASM24Controller.set_pcie_power(True)
    if self._handle is None:
      self._connect()
    if self._handle is None:
      raise usb1.USBErrorNoDevice
    self._handle.controlWrite(0x40, 0xF3, 1, 0, b"", timeout=10000)


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
  this is a best-effort readiness gate, not a hard hardware assertion.

  Only *reads* the PCIe link state, and sends PCIe power-on at most once and only while
  the link is down - same as tinygrad's own CustomASM24Controller init. This previously
  used flash.link_up(), which re-sends power-on on every poll even with the link already
  up; doing that a few seconds before tinygrad opens the GPU is the prime suspect for the
  in-car big-model load hanging in its USB weight upload."""
  asm = ChestnutUsb()
  consecutive = 0
  powered_on = False
  deadline = time.monotonic() + timeout
  try:
    while time.monotonic() < deadline:
      try:
        ltssm = asm.read_ltssm()
        if ltssm != CHESTNUT_PCIE_READY and not powered_on:
          asm.power_on_pcie()
          powered_on = True
          ltssm = asm.read_ltssm()
        voltage, current, fault = asm.read_ina()
      except Exception:
        consecutive = 0
      else:
        reading = _Reading(voltage, current, fault, ltssm)
        consecutive = consecutive + 1 if chestnut_ready(reading) else 0
        if consecutive >= stable_reads:
          return True
      time.sleep(interval)
  finally:
    asm.close()
  return False
