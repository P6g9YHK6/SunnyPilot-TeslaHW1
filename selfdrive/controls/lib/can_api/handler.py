import cereal.messaging as messaging
from openpilot.common.params import Params
from opendbc.car.can_definitions import CanData
from openpilot.selfdrive.pandad import can_list_to_can_capnp
from opendbc.can import CANPacker
from opendbc.can.dbc import DBC
from opendbc.car.values import PLATFORMS


class CanApiHandler:
  def __init__(self):
    self.params = Params()
    self.pm = messaging.PubMaster(['sendcan'])
    self._packer = None
    self._dbc = None
    self._dbc_names = None

  @property
  def dbc_names(self):
    if self._dbc_names is not None:
      return self._dbc_names
    cp_raw = self.params.get("CarParamsCache")
    if cp_raw is None:
      return None
    from cereal import car
    with car.CarParams.from_bytes(cp_raw) as cp:
      fingerprint = cp.carFingerprint
    platform = PLATFORMS.get(fingerprint)
    if platform is None:
      return None
    self._dbc_names = {str(b): n for b, n in platform.config.dbc_dict.items()}
    return self._dbc_names

  @property
  def dbc(self):
    names = self.dbc_names
    if names is None:
      return None
    dbc_name = names.get('party') or names.get('pt') or names.get('main') or next(iter(names.values()))
    if dbc_name is None:
      return None
    if self._dbc is None or self._dbc.name != dbc_name:
      self._dbc = DBC(dbc_name)
    return self._dbc

  @property
  def packer(self):
    dbc = self.dbc
    if dbc is None:
      return None
    if self._packer is None or self._packer.dbc.name != dbc.name:
      self._packer = CANPacker(dbc.name)
    return self._packer

  def send_raw(self, address: int, data: bytes, bus: int) -> bool:
    self.pm.send('sendcan', can_list_to_can_capnp([CanData(address, data, bus)], msgtype='sendcan'))
    return True

  def send_signal(self, msg_name: str, values: dict[str, float], bus: int = 0) -> dict | None:
    packer = self.packer
    if packer is None:
      return None
    addr, dat, bus_out = packer.make_can_msg(msg_name, bus, values)
    if addr == 0 and len(dat) == 0:
      return None
    self.send_raw(addr, dat, bus_out)
    return {'address': addr, 'data': dat.hex(), 'bus': bus_out}

  def get_signals(self) -> list[dict]:
    dbc = self.dbc
    if dbc is None:
      return []
    msgs = []
    for msg in dbc.msgs.values():
      sigs = []
      for sig in msg.sigs.values():
        sigs.append({
          'name': sig.name,
          'start_bit': sig.start_bit,
          'size': sig.size,
          'factor': sig.factor,
          'offset': sig.offset,
          'is_signed': sig.is_signed,
          'is_little_endian': sig.is_little_endian,
          'type': sig.type,
        })
      msgs.append({
        'name': msg.name,
        'address': msg.address,
        'size': msg.size,
        'signals': sigs,
      })
    return msgs
