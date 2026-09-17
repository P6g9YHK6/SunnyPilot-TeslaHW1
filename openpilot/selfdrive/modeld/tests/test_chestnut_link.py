from unittest.mock import patch

from openpilot.common.hardware.usb import CHESTNUT_POWERED_VOLTAGE
from openpilot.selfdrive.modeld import chestnut_link

READY_READING = (CHESTNUT_POWERED_VOLTAGE, 0, False)  # (supplyVoltage, supplyCurrent, supplyFault)
NOT_POWERED_READING = (0, 0, False)


class _USBErrorStub(Exception):
  """Stands in for usb1.USBError/USBErrorNoDevice without depending on real hardware."""


def _sequence(values):
  """Returns a mock side_effect that yields `values` in order, repeating the last
  one once exhausted (so a short list still covers a run past its length). Any
  Exception instance in the list is raised instead of returned."""
  values = list(values)
  def side_effect(*_args, **_kwargs):
    value = values[0] if len(values) == 1 else values.pop(0)
    if isinstance(value, Exception):
      raise value
    return value
  return side_effect


def _patch_probe(link_up_values, ina_values):
  return (
    patch.object(chestnut_link, "link_up", side_effect=_sequence(link_up_values)),
    patch.object(chestnut_link.ChestnutUsb, "read_ina", side_effect=_sequence(ina_values)),
  )


def test_always_ready_returns_true_quickly():
  link_up_patch, ina_patch = _patch_probe([True], [READY_READING])
  with link_up_patch, ina_patch:
    start = chestnut_link.time.monotonic()
    assert chestnut_link.wait_for_stable_chestnut(timeout=3.0, interval=0.01, stable_reads=3) is True
    # 3 stable reads at a 0.01s interval should resolve well under the 3s timeout
    assert chestnut_link.time.monotonic() - start < 1.0


def test_always_not_ready_returns_false_after_timeout():
  link_up_patch, ina_patch = _patch_probe([False], [NOT_POWERED_READING])
  with link_up_patch, ina_patch:
    assert chestnut_link.wait_for_stable_chestnut(timeout=0.2, interval=0.05, stable_reads=3) is False


def test_flapping_resets_debounce_then_succeeds():
  # not-ready, not-ready, ready, ready, ready - proves a bad read anywhere in the
  # streak resets the counter rather than just needing 3 ready reads total.
  link_up_values = [False, False, True, True, True]
  ina_values = [NOT_POWERED_READING, NOT_POWERED_READING, READY_READING, READY_READING, READY_READING]
  link_up_patch, ina_patch = _patch_probe(link_up_values, ina_values)
  with link_up_patch, ina_patch:
    assert chestnut_link.wait_for_stable_chestnut(timeout=3.0, interval=0.01, stable_reads=3) is True


def test_intermittent_exceptions_reset_but_eventually_succeed():
  # one bad read shouldn't raise out of wait_for_stable_chestnut() - it should
  # just reset the debounce streak and keep polling until stable_reads succeeds.
  ina_values = [_USBErrorStub("transient"), READY_READING, READY_READING, READY_READING]
  link_up_patch, ina_patch = _patch_probe([True], ina_values)
  with link_up_patch, ina_patch:
    assert chestnut_link.wait_for_stable_chestnut(timeout=3.0, interval=0.01, stable_reads=3) is True
