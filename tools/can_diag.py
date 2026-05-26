#!/usr/bin/env python3
"""
CAN Bus Diagnostic Tool — comprehensive CAN analysis suite.

Analyse, decode, discover, and diagnose CAN bus traffic for vehicle
reverse engineering and openpilot development.

Usage:
    # Live monitoring on device via cereal messaging
    python can_diag.py monitor --dbc tesla_can.dbc

    # Live monitoring via USB-connected Panda
    python can_diag.py monitor --panda --dbc tesla_can.dbc

    # Decode a CAN dump file
    python can_diag.py decode dump.json --dbc tesla_can.dbc

    # Discover unknown signals / patterns
    python can_diag.py discover --panda --duration 120

    # Bus health check
    python can_diag.py health --panda

    # List all signals (known + unknown) with statistics
    python can_diag.py signals --panda --dbc tesla_can.dbc

    # Live monitor with Tesla-specific 0x348 ignition tracking
    python can_diag.py monitor --panda --tesla-ignition
"""

import argparse
import collections
import csv
import json
import os
import re
import struct
import sys
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Set, TextIO, Tuple

# Auto-setup PYTHONPATH for on-device use (comma three / openpilot)
_THIS_DIR = Path(__file__).resolve().parent
_OPENPILOT_DIR = _THIS_DIR.parent if (_THIS_DIR.name == 'tools' and (_THIS_DIR.parent / 'system').exists()) else None
if _OPENPILOT_DIR and str(_OPENPILOT_DIR) not in sys.path:
    sys.path.insert(0, str(_OPENPILOT_DIR))
if _OPENPILOT_DIR and str(_OPENPILOT_DIR / 'cereal') not in sys.path:
    sys.path.insert(0, str(_OPENPILOT_DIR / 'cereal'))

# ---------------------------------------------------------------------------
# DBC Parsing
# ---------------------------------------------------------------------------

class SignalOrder(IntEnum):
    LITTLE_ENDIAN = 1
    BIG_ENDIAN = 0


class SignalSign(IntEnum):
    UNSIGNED = 0
    SIGNED = 1


@dataclass
class DBCSignal:
    name: str
    start_bit: int
    length: int
    order: SignalOrder
    sign: SignalSign
    scale: float = 1.0
    offset: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    unit: str = ""
    receiver: str = ""
    multiplexer: str = ""
    multiplexer_switch: Optional[int] = None
    val_desc: Dict[int, str] = field(default_factory=dict)

    def decode(self, data: bytes) -> Optional[float]:
        if len(data) * 8 < self.start_bit + self.length:
            return None
        raw = self._extract_raw(data)
        if raw is None:
            return None
        if self.sign == SignalSign.SIGNED:
            if self.length < 32:
                if raw & (1 << (self.length - 1)):
                    raw -= 1 << self.length
            else:
                raw = struct.unpack('<i', struct.pack('<I', raw & 0xFFFFFFFF))[0]
        return raw * self.scale + self.offset

    def _extract_raw(self, data: bytes) -> Optional[int]:
        try:
            if self.order == SignalOrder.LITTLE_ENDIAN:
                return self._extract_le(data)
            return self._extract_be(data)
        except (ValueError, OverflowError):
            return None

    def _extract_le(self, data: bytes) -> int:
        total_bits = len(data) * 8
        bit_pos = self.start_bit
        end_bit = bit_pos + self.length - 1
        if end_bit >= total_bits:
            end_bit = total_bits - 1
        result = 0
        for i in range(self.length):
            byte_idx = (bit_pos + i) // 8
            if byte_idx >= len(data):
                break
            bit_idx = (bit_pos + i) % 8
            if data[byte_idx] & (1 << bit_idx):
                result |= 1 << i
        return result

    def _extract_be(self, data: bytes) -> int:
        total_bits = len(data) * 8
        end_bit = self.start_bit
        bit_pos = end_bit - self.length + 1
        if bit_pos < 0:
            bit_pos = 0
        result = 0
        for i in range(self.length):
            actual_bit = bit_pos + i
            if actual_bit > end_bit:
                break
            if actual_bit >= total_bits:
                break
            byte_idx = actual_bit // 8
            bit_idx = 7 - (actual_bit % 8)
            if byte_idx < len(data) and (data[byte_idx] & (1 << bit_idx)):
                result |= 1 << (self.length - 1 - i)
        return result


@dataclass
class DBCMessage:
    id: int
    name: str
    size: int
    sender: str = ""
    comment: str = ""
    signals: Dict[str, DBCSignal] = field(default_factory=dict)
    multiplexor_signal: Optional[str] = None

    def get_signal(self, name: str) -> Optional[DBCSignal]:
        return self.signals.get(name)

    def decode(self, data: bytes, multiplexer_value: Optional[int] = None) -> Dict[str, Optional[float]]:
        result: Dict[str, Optional[float]] = {}
        for sig in self.signals.values():
            if sig.multiplexer_switch is not None:
                if multiplexer_value is None or sig.multiplexer_switch != multiplexer_value:
                    continue
            result[sig.name] = sig.decode(data)
        return result


class DBCParser:
    """Parse .dbc (CAN Database) files into structured definitions."""

    RE_VERSION = re.compile(r'VERSION\s+"([^"]*)"')
    RE_BU = re.compile(r'BU_: (.+)')
    RE_BO = re.compile(r'BO_ (\d+) (\w+): (\d+) (\w+)')
    RE_SG = re.compile(
        r'SG_ (\w+)\s*(M|m\d+)?\s*:\s*(\d+)\|(\d+)@(\d)([+-])'
        r'\s+\(([^)]+)\)\s+\[([^\]]*)\]\s+(\S+)\s+(.+)'
    )
    RE_CM_BO = re.compile(r'CM_ BO_ (\d+) "(.+)"')
    RE_CM_SG = re.compile(r'CM_ SG_ (\d+) (\w+) "(.+)"')
    RE_VAL = re.compile(r'VAL_ (\d+) (\w+) (.+)')

    def __init__(self, dbc_path: str):
        self.path = dbc_path
        self.version: str = ""
        self.nodes: List[str] = []
        self.messages: Dict[int, DBCMessage] = {}
        self.name_to_id: Dict[str, int] = {}
        self._parse()

    def _parse(self) -> None:
        current_msg: Optional[DBCMessage] = None
        current_val_msg: Optional[int] = None
        current_val_sig: Optional[str] = None

        with open(self.path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('BS_:'):
                    continue

                m = self.RE_VERSION.match(line)
                if m:
                    self.version = m.group(1)
                    continue

                m = self.RE_BU.match(line)
                if m:
                    self.nodes = m.group(1).split()
                    continue

                m = self.RE_BO.match(line)
                if m:
                    msg_id = int(m.group(1))
                    msg = DBCMessage(
                        id=msg_id,
                        name=m.group(2),
                        size=int(m.group(3)),
                        sender=m.group(4),
                    )
                    self.messages[msg_id] = msg
                    self.name_to_id[msg.name] = msg_id
                    current_msg = msg
                    continue

                if current_msg is not None:
                    m = self.RE_SG.match(line)
                    if m:
                        sig_name = m.group(1)
                        mul = m.group(2) or ""
                        start_bit = int(m.group(3))
                        length = int(m.group(4))
                        order = SignalOrder.BIG_ENDIAN if m.group(5) == '0' else SignalOrder.LITTLE_ENDIAN
                        sign = SignalSign.SIGNED if m.group(6) == '-' else SignalSign.UNSIGNED
                        scale_off = m.group(7)
                        mm = re.match(r'([\d.eE+-]+)\|([\d.eE+-]+)', scale_off)
                        scale = float(mm.group(1)) if mm else 1.0
                        offset = float(mm.group(2)) if mm else 0.0
                        r_min_max = m.group(8)
                        unit = m.group(9)
                        receiver = m.group(10)

                        sig = DBCSignal(
                            name=sig_name, start_bit=start_bit, length=length,
                            order=order, sign=sign, scale=scale, offset=offset,
                            unit=unit, receiver=receiver,
                        )
                        if mul == 'M':
                            sig.multiplexer = 'M'
                            current_msg.multiplexor_signal = sig_name
                        elif mul.startswith('m'):
                            sig.multiplexer = mul
                            sig.multiplexer_switch = int(mul[1:])
                        if r_min_max:
                            try:
                                parts = r_min_max.split('|')
                                sig.min_val = float(parts[0])
                                sig.max_val = float(parts[1]) if len(parts) > 1 else sig.min_val
                            except ValueError:
                                pass
                        current_msg.signals[sig_name] = sig
                        continue

                m = self.RE_CM_BO.match(line)
                if m:
                    msg_id = int(m.group(1))
                    if msg_id in self.messages:
                        self.messages[msg_id].comment = m.group(2)
                    continue

                m = self.RE_CM_SG.match(line)
                if m:
                    msg_id = int(m.group(1))
                    sig_name = m.group(2)
                    if msg_id in self.messages and sig_name in self.messages[msg_id].signals:
                        self.messages[msg_id].signals[sig_name].name = m.group(3)
                    continue

                m = self.RE_VAL.match(line)
                if m:
                    msg_id = int(m.group(1))
                    sig_name = m.group(2)
                    val_str = m.group(3)
                    if msg_id in self.messages and sig_name in self.messages[msg_id].signals:
                        descs = re.findall(r'(\d+)\s+"([^"]*)"', val_str)
                        for v, d in descs:
                            self.messages[msg_id].signals[sig_name].val_desc[int(v)] = d
                    continue

    def get_message_by_id(self, msg_id: int) -> Optional[DBCMessage]:
        return self.messages.get(msg_id)

    def get_message_by_name(self, name: str) -> Optional[DBCMessage]:
        mid = self.name_to_id.get(name)
        return self.messages.get(mid) if mid is not None else None

    def get_signal(self, msg_id: int, sig_name: str) -> Optional[DBCSignal]:
        msg = self.messages.get(msg_id)
        if msg is None:
            return None
        return msg.signals.get(sig_name)

    def find_matching_messages(self, addr: int, dlc: int) -> List[DBCMessage]:
        results = []
        for msg in self.messages.values():
            if msg.id == addr:
                results.append(msg)
        return results


# ---------------------------------------------------------------------------
# CAN Capture Backends
# ---------------------------------------------------------------------------

@dataclass
class CANFrame:
    bus: int
    address: int
    data: bytes
    timestamp: float
    fd: bool = False

    def hex(self) -> str:
        return self.data.hex()

    def __repr__(self) -> str:
        return f"CAN({self.bus:1d} {self.address:03X} [{len(self.data)}] {self.hex()})"


class CANCaptureBackend(ABC):
    @abstractmethod
    def recv(self, timeout: float = 1.0) -> List[CANFrame]:
        ...

    @abstractmethod
    def close(self) -> None:
        ...


class PandaBackend(CANCaptureBackend):
    def __init__(self, serial: Optional[str] = None, bus: int = 0):
        from panda import Panda
        self._panda: Optional[Panda] = None
        self.bus = bus
        if serial:
            self._panda = Panda(serial)
        else:
            pandas = Panda.list()
            if not pandas:
                raise RuntimeError("No Panda found")
            self._panda = Panda(pandas[0])
        self._panda.set_safety_mode(0xFFFF)  # SAFETY_SILENT
        self._panda.can_clear(0xFFFF)

    def recv(self, timeout: float = 1.0) -> List[CANFrame]:
        if self._panda is None:
            return []
        msgs = self._panda.can_recv()
        now = time.monotonic()
        frames = []
        for addr, ts, data, bus_src in msgs:
            frames.append(CANFrame(bus=bus_src, address=addr, data=bytes(data), timestamp=now))
        return frames

    def close(self) -> None:
        if self._panda:
            self._panda.close()
            self._panda = None


class MessagingBackend(CANCaptureBackend):
    def __init__(self, service: str = 'can'):
        import cereal.messaging as messaging
        self._sock = messaging.sub_sock(service, conflate=True, timeout=0)

    def recv(self, timeout: float = 1.0) -> List[CANFrame]:
        import cereal.messaging as messaging
        frames = []
        end = time.monotonic() + timeout
        while True:
            cans = messaging.drain_sock(self._sock)
            if cans:
                for cmsg in cans:
                    for msg in cmsg.can:
                        dat = bytes(msg.dat)
                        frames.append(CANFrame(
                            bus=msg.bus,
                            address=msg.address,
                            data=dat,
                            timestamp=time.monotonic(),
                            fd=bool(msg.fd) if hasattr(msg, 'fd') else False,
                        ))
            if frames or time.monotonic() >= end:
                break
            time.sleep(0.001)
        return frames

    def close(self) -> None:
        pass


class LogFileBackend(CANCaptureBackend):
    """Replay CAN frames from a JSON dump (list of {bus, address, data, timestamp})."""

    def __init__(self, path: str):
        with open(path, 'r') as f:
            self._frames = json.load(f)
        self._idx = 0
        self._start_time = time.monotonic()
        if self._frames and 'timestamp' in self._frames[0]:
            self._base_ts = self._frames[0]['timestamp']
        else:
            self._base_ts = 0

    def recv(self, timeout: float = 1.0) -> List[CANFrame]:
        now = time.monotonic()
        elapsed = now - self._start_time
        result = []
        while self._idx < len(self._frames):
            f = self._frames[self._idx]
            if f['timestamp'] - self._base_ts > elapsed:
                break
            result.append(CANFrame(
                bus=f.get('bus', 0),
                address=f['address'],
                data=bytes.fromhex(f['data']) if isinstance(f['data'], str) else bytes(f['data']),
                timestamp=f.get('timestamp', 0),
            ))
            self._idx += 1
        return result

    def close(self) -> None:
        pass


def open_can_capture(source: str = 'panda', **kwargs) -> CANCaptureBackend:
    if source == 'panda':
        return PandaBackend(**kwargs)
    elif source == 'messaging':
        return MessagingBackend(**kwargs)
    elif source == 'log':
        return LogFileBackend(kwargs.get('path', ''))
    else:
        raise ValueError(f"Unknown source: {source}")


# ---------------------------------------------------------------------------
# Known-signal tracker  (decodes & samples known DBC signals)
# ---------------------------------------------------------------------------

@dataclass
class SignalSample:
    timestamp: float
    raw_value: float
    physical_value: float


class SignalTracker:
    """Collect time-series samples for all signals defined in a DBC."""

    def __init__(self, dbc: DBCParser):
        self.dbc = dbc
        self.samples: Dict[int, Dict[str, List[SignalSample]]] = defaultdict(lambda: defaultdict(list))
        self._prev_counters: Dict[int, int] = {}

    def process_frame(self, frame: CANFrame, multiplex: Optional[int] = None) -> Dict[str, Optional[float]]:
        msg = self.dbc.get_message_by_id(frame.address)
        if msg is None:
            return {}
        decoded = msg.decode(frame.data, multiplex)
        t = frame.timestamp
        for sig_name, val in decoded.items():
            if val is not None:
                self.samples[frame.address][sig_name].append(SignalSample(t, val, val))
        return decoded

    def get_signal_values(self, msg_id: int, sig_name: str) -> List[SignalSample]:
        return self.samples.get(msg_id, {}).get(sig_name, [])

    def summary(self, msg_id: int, sig_name: str) -> Dict[str, Any]:
        vals = [s.physical_value for s in self.samples.get(msg_id, {}).get(sig_name, [])]
        if not vals:
            return {}
        return {
            'count': len(vals),
            'min': min(vals),
            'max': max(vals),
            'avg': sum(vals) / len(vals),
            'unique': len(set(vals)),
        }

    def reset(self) -> None:
        self.samples.clear()
        self._prev_counters.clear()


# ---------------------------------------------------------------------------
# Unknown-signal discovery
# ---------------------------------------------------------------------------

@dataclass
class UnknownMessageState:
    address: int
    bus: int
    dlc: int
    count: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0
    value_history: List[bytes] = field(default_factory=list)
    byte_min: List[int] = field(default_factory=lambda: [255] * 8)
    byte_max: List[int] = field(default_factory=lambda: [0] * 8)
    bit_changes: List[int] = field(default_factory=lambda: [0] * 64)
    prev_data: Optional[bytes] = None

    # Rolling-counter detection
    counter_candidates: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Checksum candidates
    checksum_candidates: List[Dict[str, Any]] = field(default_factory=list)

    # Cycle time estimation
    cycle_times: List[float] = field(default_factory=list)
    est_frequency: float = 0.0

    def update(self, frame: CANFrame) -> None:
        if self.count == 0:
            self.first_seen = frame.timestamp
            self.dlc = len(frame.data)
            self.bus = frame.bus
        self.last_seen = frame.timestamp
        self.count += 1

        if self.prev_data is not None and len(frame.data) == len(self.prev_data):
            for byte_idx in range(min(len(frame.data), 8)):
                b = frame.data[byte_idx]
                if b < self.byte_min[byte_idx]:
                    self.byte_min[byte_idx] = b
                if b > self.byte_max[byte_idx]:
                    self.byte_max[byte_idx] = b
                changed = self.prev_data[byte_idx] ^ b
                for bit in range(8):
                    if changed & (1 << bit):
                        bit_pos = byte_idx * 8 + bit
                        if bit_pos < 64:
                            self.bit_changes[bit_pos] += 1

        # cycle time
        if len(self.cycle_times) < 100:
            self.cycle_times.append(frame.timestamp)
        elif len(self.cycle_times) == 100:
            if self.cycle_times[-1] - self.cycle_times[0] > 0:
                self.est_frequency = len(self.cycle_times) / (self.cycle_times[-1] - self.cycle_times[0])
            self.cycle_times.pop(0)
            self.cycle_times.append(frame.timestamp)

        # Keep last 5 samples for counter analysis
        self.value_history.append(bytes(frame.data))
        if len(self.value_history) > 5:
            self.value_history.pop(0)

        self.prev_data = bytes(frame.data)


class UnknownSignalTracker:
    """Analyse CAN IDs not found in any DBC to discover signal patterns."""

    def __init__(self):
        self.unknown: Dict[int, UnknownMessageState] = {}
        self.all_ids: Dict[int, UnknownMessageState] = {}
        self._prev_counters: Dict[int, Dict[int, int]] = defaultdict(dict)

    def process_frame(self, frame: CANFrame, known_ids: Set[int]) -> None:
        if frame.address not in self.all_ids:
            self.all_ids[frame.address] = UnknownMessageState(address=frame.address, bus=frame.bus, dlc=len(frame.data))
        self.all_ids[frame.address].update(frame)

        if frame.address not in known_ids:
            if frame.address not in self.unknown:
                self.unknown[frame.address] = UnknownMessageState(address=frame.address, bus=frame.bus, dlc=len(frame.data))
            self.unknown[frame.address].update(frame)

    def detect_counters(self, msg_id: int) -> List[Dict[str, Any]]:
        state = self.unknown.get(msg_id) or self.all_ids.get(msg_id)
        if state is None or len(state.value_history) < 3:
            return []

        counters = []
        for byte_idx in range(state.dlc):
            vals = [h[byte_idx] for h in state.value_history]
            # Check nibble-level rolling counters
            for nibble_shift in [0, 4]:
                nibble_vals = [(v >> nibble_shift) & 0xF for v in vals]
                if self._is_counter(nibble_vals):
                    counters.append({
                        'byte': byte_idx,
                        'nibble': 'high' if nibble_shift == 4 else 'low',
                        'max': 15,
                        'sequence': nibble_vals,
                    })
            # Check full-byte counter
            if self._is_counter(vals):
                counters.append({
                    'byte': byte_idx,
                    'nibble': 'full',
                    'max': 255,
                    'sequence': vals,
                })
        return counters

    def detect_checksums(self, msg_id: int) -> List[Dict[str, Any]]:
        state = self.unknown.get(msg_id)
        if state is None or len(state.value_history) < 4:
            return []

        candidates = []
        data_len = state.dlc
        # Last byte is often checksum
        for checksum_byte in range(max(0, data_len - 2), data_len):
            samples = [h[checksum_byte] for h in state.value_history[:20]]
            if len(set(samples)) > 10:
                candidates.append({
                    'byte': checksum_byte,
                    'samples': samples[:10],
                    'note': 'high entropy — possible checksum or counter',
                })
        return candidates

    def detect_static_bits(self, msg_id: int) -> List[int]:
        state = self.unknown.get(msg_id) or self.all_ids.get(msg_id)
        if state is None:
            return []
        static = []
        for bit_idx in range(state.dlc * 8):
            if state.bit_changes[bit_idx] == 0 and state.count > 5:
                static.append(bit_idx)
        return static

    def summary(self, msg_id: int) -> Dict[str, Any]:
        state = self.unknown.get(msg_id)
        if state is None:
            return {}
        return {
            'address': f"{msg_id:03X}",
            'bus': state.bus,
            'dlc': state.dlc,
            'count': state.count,
            'duration': state.last_seen - state.first_seen,
            'frequency_hz': round(state.est_frequency, 1) if state.est_frequency else None,
            'byte_ranges': [
                f"{state.byte_min[i]:02X}-{state.byte_max[i]:02X}"
                for i in range(state.dlc)
            ],
            'changing_bits': sum(1 for c in state.bit_changes[:state.dlc * 8] if c > 0),
            'counters': self.detect_counters(msg_id),
            'checksums': self.detect_checksums(msg_id),
        }

    @staticmethod
    def _is_counter(vals: List[int]) -> bool:
        if len(vals) < 3:
            return False
        diffs = []
        for i in range(1, len(vals)):
            d = (vals[i] - vals[i - 1]) & 0xFF
            if d > 0 and d <= 3:
                diffs.append(d)
        return len(diffs) >= 2


# ---------------------------------------------------------------------------
# Bus Health
# ---------------------------------------------------------------------------

@dataclass
class BusHealth:
    bus_number: int
    total_frames: int = 0
    unique_ids: int = 0
    errors: int = 0
    bus_load_pct: float = 0.0
    bitrate: int = 500000
    start_time: float = 0.0

    def frame_rate(self) -> float:
        elapsed = time.monotonic() - self.start_time
        return self.total_frames / elapsed if elapsed > 0 else 0

    def load_estimate(self) -> float:
        """Estimate bus load based on frame rate and average frame size."""
        avg_bits_per_frame = 80  # ~10 bytes + overhead
        return (self.frame_rate() * avg_bits_per_frame / self.bitrate) * 100


class HealthChecker:
    def __init__(self):
        self.buses: Dict[int, BusHealth] = {}
        self.bus_frames: Dict[int, Set[int]] = defaultdict(set)
        self._last_print = 0

    def process_frame(self, frame: CANFrame) -> None:
        if frame.bus not in self.buses:
            self.buses[frame.bus] = BusHealth(bus_number=frame.bus, start_time=time.monotonic())
        self.buses[frame.bus].total_frames += 1
        self.bus_frames[frame.bus].add(frame.address)

    def report(self) -> Dict[int, Dict[str, Any]]:
        result = {}
        for bus_num, bh in self.buses.items():
            bh.unique_ids = len(self.bus_frames[bus_num])
            result[bus_num] = {
                'bus': bus_num,
                'total_frames': bh.total_frames,
                'unique_ids': bh.unique_ids,
                'frame_rate': round(bh.frame_rate(), 1),
                'bus_load_pct': round(bh.load_estimate(), 1),
                'bitrate': bh.bitrate,
            }
        return result


# ---------------------------------------------------------------------------
# Tesla-specific helpers
# ---------------------------------------------------------------------------

def check_tesla_ignition(frame: CANFrame) -> bool:
    """Check if a CAN frame indicates Tesla AP1 ignition (0x348 GTW_status)."""
    if frame.address == 0x348 and len(frame.data) >= 7:
        return bool(frame.data[0] & 0x01)
    return False


class TeslaIgnitionMonitor:
    def __init__(self):
        self._prev_counter: Dict[int, int] = {}
        self.ignition_detected: bool = False
        self._last_seen: float = 0.0

    def process_frame(self, frame: CANFrame) -> bool:
        if frame.address == 0x348 and len(frame.data) >= 7 and (frame.data[0] & 0x01):
            counter = frame.data[6] & 0x0F
            prev = self._prev_counter.get(0x348, -1)
            if prev != -1:
                expected = (prev + 1) & 0x0F
                if counter == expected:
                    self.ignition_detected = True
            self._prev_counter[0x348] = counter
            self._last_seen = time.monotonic()
            return self.ignition_detected
        if time.monotonic() - self._last_seen > 2.0:
            self.ignition_detected = False
        return self.ignition_detected


# ---------------------------------------------------------------------------
# Display / Formatter helpers
# ---------------------------------------------------------------------------

def format_frame(frame: CANFrame, decoded: Optional[Dict[str, Optional[float]]] = None) -> str:
    data_str = ' '.join(f"{b:02X}" for b in frame.data)
    line = f"[{frame.timestamp:8.3f}] BUS{frame.bus}  {frame.address:03X}  ({len(frame.data):2d})  {data_str}"
    if decoded:
        parts = []
        for name, val in decoded.items():
            if val is not None:
                parts.append(f"{name}={val:.3f}")
            else:
                parts.append(f"{name}=?")
        if parts:
            line += f"  |  {', '.join(parts)}"
    return line


def signal_table(counts: List[Tuple[int, int]]) -> str:
    """Show frequency table of CAN IDs."""
    if not counts:
        return ""
    total = sum(c for _, c in counts)
    lines = ["ID      Count     %     Name"]
    for addr, cnt in sorted(counts, key=lambda x: -x[1])[:50]:
        pct = cnt / total * 100 if total else 0
        lines.append(f"{addr:03X}  {cnt:8d}  {pct:5.1f}")
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Main Diagnostic Tool
# ---------------------------------------------------------------------------

class CANDiag:
    def __init__(self):
        self.dbc: Optional[DBCParser] = None
        self.backend: Optional[CANCaptureBackend] = None
        self.signal_tracker: Optional[SignalTracker] = None
        self.unknown_tracker = UnknownSignalTracker()
        self.health_checker = HealthChecker()
        self.tesla_ignition = TeslaIgnitionMonitor()
        self.known_ids: Set[int] = set()
        self._running = False

    @staticmethod
    def _find_dbc(path: Optional[str]) -> Optional[str]:
        if path and os.path.exists(path):
            return path
        # Search common DBC locations
        search_dirs = []
        if _OPENPILOT_DIR:
            search_dirs.append(_OPENPILOT_DIR / 'opendbc' / 'dbc')
            search_dirs.append(_OPENPILOT_DIR / 'opendbc_repo' / 'opendbc' / 'dbc')
        # Try to detect from CarParams on device
        if _OPENPILOT_DIR:
            try:
                sys.path.insert(0, str(_OPENPILOT_DIR))
                from openpilot.common.params import Params
                from opendbc import DBC_PATH
                p = Params()
                cp_bytes = p.get('CarParams')
                if cp_bytes is not None and len(cp_bytes) > 4:
                    from opendbc.car.structs import CarParams
                    cp = CarParams.from_bytes(cp_bytes)
                    for car_dbc in getattr(cp, 'dbc', []):
                        full = os.path.join(DBC_PATH, car_dbc)
                        if os.path.exists(full):
                            return full
                    # fallback: try DBC_PATH directory
                    search_dirs.append(Path(DBC_PATH))
            except Exception:
                pass
        for d in search_dirs:
            if d.exists():
                for f in sorted(d.iterdir()):
                    if f.suffix == '.dbc':
                        return str(f)
        return None

    def load_dbc(self, path: Optional[str]) -> None:
        resolved = self._find_dbc(path)
        if resolved:
            self.dbc = DBCParser(resolved)
            self.signal_tracker = SignalTracker(self.dbc)
            self.known_ids = set(self.dbc.messages.keys())
            print(f"  Loaded DBC: {os.path.basename(resolved)} ({len(self.dbc.messages)} messages, "
                  f"{sum(len(m.signals) for m in self.dbc.messages.values())} signals)")
        elif path:
            print(f"  DBC not found: {path}")

    def connect(self, source: str = 'panda', **kwargs) -> None:
        self.backend = open_can_capture(source, **kwargs)
        print(f"  Connected via: {source}")

    # ---- mode: monitor ----

    def mode_monitor(self, args: argparse.Namespace) -> None:
        """Live CAN traffic monitor with optional DBC decoding."""
        self.load_dbc(args.dbc)
        self.connect(args.source)

        freq_counter: Dict[int, int] = defaultdict(int)
        last_print = time.monotonic()
        frame_count = 0
        print(f"\n{'='*70}")
        print(f"  CAN Monitor — {' '.join(sys.argv[1:])}")
        print(f"{'='*70}\n")
        print("  Press Ctrl+C to stop\n")

        if args.filter_id:
            filter_ids = {int(x, 16) for x in args.filter_id.split(',')}
        else:
            filter_ids = None

        self._running = True
        try:
            while self._running:
                frames = self.backend.recv(timeout=0.1) if hasattr(self.backend, 'recv') else []
                for frame in frames:
                    if filter_ids and frame.address not in filter_ids:
                        continue
                    frame_count += 1
                    freq_counter[frame.address] += 1
                    self.health_checker.process_frame(frame)

                    decoded = None
                    if self.dbc and frame.address in self.known_ids:
                        decoded = self.dbc.get_message_by_id(frame.address).decode(frame.data)

                    if args.tesla_ignition:
                        self.tesla_ignition.process_frame(frame)

                    print(format_frame(frame, decoded))

                if time.monotonic() - last_print >= 5:
                    print(f"\n  --- {frame_count} frames in 5s ---")
                    if args.tesla_ignition:
                        ign = "YES" if self.tesla_ignition.ignition_detected else "NO"
                        print(f"  Tesla Ignition (0x348): {ign}")
                    last_print = time.monotonic()
                    frame_count = 0
        except KeyboardInterrupt:
            pass
        finally:
            self._print_stats(freq_counter)

    # ---- mode: decode ----

    def mode_decode(self, args: argparse.Namespace) -> None:
        """Decode live CAN traffic using a DBC file."""
        self.load_dbc(args.dbc)
        if self.dbc is None:
            print("ERROR: --dbc is required for decode mode")
            return

        self.connect(args.source)

        print(f"\n{'='*70}")
        print("  Decode Mode — DBC signal decoding")
        print(f"{'='*70}\n")

        self._running = True
        try:
            while self._running:
                frames = self.backend.recv(timeout=0.5)
                for frame in frames:
                    decoded = self._decode_frame(frame)
                    if decoded:
                        print(format_frame(frame, decoded))
        except KeyboardInterrupt:
            pass

    def _decode_frame(self, frame: CANFrame) -> Optional[Dict[str, Optional[float]]]:
        if self.dbc is None:
            return None
        msg = self.dbc.get_message_by_id(frame.address)
        if msg is None:
            return None
        return msg.decode(frame.data)

    # ---- mode: discover ----

    def mode_discover(self, args: argparse.Namespace) -> None:
        """Discover unknown CAN signals and patterns."""
        self.load_dbc(args.dbc)
        self.connect(args.source)

        duration = args.duration or 60
        print(f"\n{'='*70}")
        print(f"  Discovery Mode — collecting for {duration}s")
        print(f"{'='*70}\n")

        start = time.monotonic()
        self._running = True
        try:
            while self._running and time.monotonic() - start < duration:
                frames = self.backend.recv(timeout=0.1)
                for frame in frames:
                    self.unknown_tracker.process_frame(frame, self.known_ids)
        except KeyboardInterrupt:
            pass

        print(f"\nCollected {len(self.unknown_tracker.all_ids)} unique IDs\n")

        # Report unknown IDs with analysis
        print(f"{'='*70}")
        print("  UNKNOWN MESSAGES (not in DBC)")
        print(f"{'='*70}")
        unknowns = sorted(self.unknown_tracker.unknown.items(), key=lambda x: x[1].count, reverse=True)
        for addr, state in unknowns:
            s = self.unknown_tracker.summary(addr)
            print(f"\n  {s['address']}  bus={s['bus']}  dlc={s['dlc']}  "
                  f"count={s['count']}  freq={s['frequency_hz']}Hz  "
                  f"changing_bits={s['changing_bits']}/{s['dlc']*8}")
            print(f"    Byte ranges: {', '.join(s['byte_ranges'])}")
            if s['counters']:
                for c in s['counters']:
                    print(f"    COUNTER: byte={c['byte']} nibble={c['nibble']} seq={c['sequence'][-5:]}")
            if s['checksums']:
                for c in s['checksums']:
                    print(f"    CHECKSUM: byte={c['byte']} {c['note']}")

        # Report known ID frequency
        print(f"\n{'='*70}")
        print("  ALL MESSAGE FREQUENCIES")
        print(f"{'='*70}")
        all_addrs = sorted(self.unknown_tracker.all_ids.items(), key=lambda x: x[1].count, reverse=True)
        for addr, state in all_addrs[:60]:
            freq = f"{state.est_frequency:.1f}Hz" if state.est_frequency else "?"
            known = "KNOWN" if addr in self.known_ids else "UNKN"
            print(f"  {addr:03X}  {state.count:8d}  {freq:>8s}  dlc={state.dlc}  {known}")

        self._save_if_requested(args, {'unknowns': [self.unknown_tracker.summary(a) for a, _ in unknowns]})

    # ---- mode: health ----

    def mode_health(self, args: argparse.Namespace) -> None:
        """CAN bus health diagnostics."""
        self.connect(args.source)
        duration = args.duration or 30

        print(f"\n{'='*70}")
        print(f"  Health Check — collecting for {duration}s")
        print(f"{'='*70}\n")

        start = time.monotonic()
        self._running = True
        try:
            while self._running and time.monotonic() - start < duration:
                frames = self.backend.recv(timeout=0.1)
                for frame in frames:
                    self.health_checker.process_frame(frame)
        except KeyboardInterrupt:
            pass

        print(f"\n{'='*70}")
        print("  BUS HEALTH REPORT")
        print(f"{'='*70}\n")
        for bus_num, report in self.health_checker.report().items():
            print(f"  Bus {bus_num}:")
            print(f"    Total frames:   {report['total_frames']}")
            print(f"    Unique IDs:     {report['unique_ids']}")
            print(f"    Frame rate:     {report['frame_rate']} msg/s")
            print(f"    Bus load:       {report['bus_load_pct']}%")
            print(f"    Bitrate:        {report['bitrate'] // 1000}kbps")
            print()

    # ---- mode: signals ----

    def mode_signals(self, args: argparse.Namespace) -> None:
        """List all known and unknown signals with statistics."""
        self.load_dbc(args.dbc)
        self.connect(args.source)
        duration = args.duration or 30

        print(f"\n{'='*70}")
        print(f"  Signal Survey — collecting for {duration}s")
        print(f"{'='*70}\n")

        start = time.monotonic()
        self._running = True
        try:
            while self._running and time.monotonic() - start < duration:
                frames = self.backend.recv(timeout=0.1)
                for frame in frames:
                    self.unknown_tracker.process_frame(frame, self.known_ids)
                    if self.dbc and self.signal_tracker and frame.address in self.known_ids:
                        self.signal_tracker.process_frame(frame)
        except KeyboardInterrupt:
            pass

        print(f"\n{'='*70}")
        print("  KNOWN SIGNALS (from DBC)")
        print(f"{'='*70}")
        if self.dbc:
            for msg_id in sorted(self.dbc.messages.keys()):
                msg = self.dbc.messages[msg_id]
                state = self.unknown_tracker.all_ids.get(msg_id)
                freq = f"{state.est_frequency:.1f}Hz" if state and state.est_frequency else "?"
                count = state.count if state else 0
                print(f"\n  {msg_id:03X}  {msg.name:30s}  count={count:6d}  freq={freq:>8s}")
                for sig_name, sig in msg.signals.items():
                    tracker_summary = {}
                    if self.signal_tracker:
                        tracker_summary = self.signal_tracker.summary(msg_id, sig_name)
                    if tracker_summary:
                        print(f"    {sig_name:25s}  [{sig.start_bit:2d}+{sig.length:2d}]  "
                              f"min={tracker_summary['min']:.2f}  max={tracker_summary['max']:.2f}  "
                              f"avg={tracker_summary['avg']:.2f}  unique={tracker_summary['unique']}")
                    else:
                        print(f"    {sig_name:25s}  [{sig.start_bit:2d}+{sig.length:2d}]  "
                              f"scale={sig.scale}  offset={sig.offset}  unit={sig.unit}")

        print(f"\n{'='*70}")
        print("  UNKNOWN SIGNALS / IDS")
        print(f"{'='*70}")
        unknowns = sorted(self.unknown_tracker.unknown.items(), key=lambda x: x[1].count, reverse=True)
        for addr, state in unknowns:
            s = self.unknown_tracker.summary(addr)
            print(f"  {s['address']}  dlc={s['dlc']}  count={s['count']}  "
                  f"freq={s['frequency_hz']}Hz  bytes=[{', '.join(s['byte_ranges'])}]")

        self._save_if_requested(args, {
            'known': [
                {'id': f"{mid:03X}", 'name': self.dbc.messages[mid].name,
                 'signals': list(self.dbc.messages[mid].signals.keys())}
                for mid in sorted(self.dbc.messages.keys())
            ] if self.dbc else [],
            'unknown': [self.unknown_tracker.summary(a) for a, _ in unknowns],
        })

    # ---- mode: tesla-ignition ----

    def mode_tesla_ignition(self, args: argparse.Namespace) -> None:
        """Monitor Tesla Legacy 0x348 ignition signal."""
        self.connect(args.source)

        print(f"\n{'='*70}")
        print("  Tesla AP1 Ignition Monitor (0x348 GTW_status)")
        print(f"{'='*70}\n")
        print("  Shift to Drive to test ignition detection\n")

        self._running = True
        last_print = time.monotonic()
        try:
            while self._running:
                frames = self.backend.recv(timeout=0.1)
                for frame in frames:
                    if frame.address == 0x348:
                        counter = frame.data[6] & 0x0F if len(frame.data) > 6 else 0
                        bit0 = frame.data[0] & 0x01 if frame.data else 0
                        print(f"  0x348  data={frame.data.hex()}  bit0={bit0}  counter={counter}")
                    self.tesla_ignition.process_frame(frame)

                if time.monotonic() - last_print > 2:
                    ign = "YES (counter rolling)" if self.tesla_ignition.ignition_detected else "NO"
                    print(f"\n  Ignition: {ign}\n")
                    last_print = time.monotonic()
        except KeyboardInterrupt:
            pass

    # ---- mode: dump ----

    def mode_dump(self, args: argparse.Namespace) -> None:
        """Dump all CAN traffic to a JSON file for later analysis."""
        self.connect(args.source)
        duration = args.duration or 60
        out_path = args.output or f"can_dump_{int(time.time())}.json"

        print(f"Dumping CAN traffic to {out_path} for {duration}s ...")
        records: List[Dict] = []
        start = time.monotonic()
        self._running = True
        try:
            while self._running and time.monotonic() - start < duration:
                frames = self.backend.recv(timeout=0.1)
                for frame in frames:
                    records.append({
                        'timestamp': frame.timestamp,
                        'bus': frame.bus,
                        'address': frame.address,
                        'data': frame.data.hex(),
                    })
        except KeyboardInterrupt:
            pass

        with open(out_path, 'w') as f:
            json.dump(records, f, indent=2)
        print(f"Saved {len(records)} frames to {out_path}")

    # ---- helpers ----

    def _print_stats(self, freq: Dict[int, int]) -> None:
        print(f"\n{'='*70}")
        print("  CAN ID FREQUENCY TABLE")
        print(f"{'='*70}")
        total = sum(freq.values())
        for addr, cnt in sorted(freq.items(), key=lambda x: -x[1])[:40]:
            name = ""
            if self.dbc and addr in self.known_ids:
                name = self.dbc.messages[addr].name
            pct = cnt / total * 100 if total else 0
            print(f"  {addr:03X}  {cnt:8d}  {pct:5.1f}%  {'('+name+')' if name else ''}")

    def _save_if_requested(self, args: argparse.Namespace, data: Dict) -> None:
        if args.save:
            with open(args.save, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"\n  Saved report to {args.save}")

    def close(self) -> None:
        if self.backend:
            self.backend.close()
        self._running = False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="CAN Bus Diagnostic Tool — analyse, decode, discover, and diagnose.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python can_diag.py monitor --panda --dbc tesla_can.dbc
  python can_diag.py monitor --panda --filter-id 348,155,370
  python can_diag.py decode --panda --dbc tesla_can.dbc
  python can_diag.py discover --panda --duration 120 --save report.json
  python can_diag.py health --panda --duration 30
  python can_diag.py signals --panda --dbc tesla_can.dbc --duration 60
  python can_diag.py tesla-ignition --panda
  python can_diag.py dump --panda --duration 30 --output capture.json
        """,
    )

    subparsers = parser.add_subparsers(dest='mode', help='Mode')

    # Common arguments
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--panda', action='store_const', const='panda', dest='source', default='panda')
    common.add_argument('--messaging', action='store_const', const='messaging', dest='source')
    common.add_argument('--log', type=str, help='Replay from JSON log file')
    common.add_argument('--dbc', type=str, default=None, help='Path to .dbc file')
    common.add_argument('--duration', type=int, default=None, help='Collection duration in seconds')
    common.add_argument('--save', type=str, default=None, help='Save report to JSON file')

    # monitor
    p_mon = subparsers.add_parser('monitor', parents=[common], help='Live CAN traffic monitor')
    p_mon.add_argument('--filter-id', type=str, help='Comma-separated hex IDs to show (e.g. 348,155,370)')
    p_mon.add_argument('--tesla-ignition', action='store_true', help='Show Tesla 0x348 ignition status')

    # decode
    p_dec = subparsers.add_parser('decode', parents=[common], help='Decode CAN messages using DBC')

    # discover
    p_dis = subparsers.add_parser('discover', parents=[common], help='Discover unknown signals and patterns')

    # health
    p_hlth = subparsers.add_parser('health', parents=[common], help='CAN bus health diagnostics')

    # signals
    p_sig = subparsers.add_parser('signals', parents=[common], help='List all known/unknown signals')

    # tesla-ignition
    p_tig = subparsers.add_parser('tesla-ignition', parents=[common], help='Monitor Tesla AP1 0x348 ignition')

    # dump
    p_dump = subparsers.add_parser('dump', parents=[common], help='Dump CAN traffic to JSON file')
    p_dump.add_argument('--output', type=str, default=None, help='Output file path')

    args = parser.parse_args()

    if args.log:
        args.source = 'log'

    diag = CANDiag()

    try:
        if args.mode == 'monitor':
            diag.mode_monitor(args)
        elif args.mode == 'decode':
            diag.mode_decode(args)
        elif args.mode == 'discover':
            diag.mode_discover(args)
        elif args.mode == 'health':
            diag.mode_health(args)
        elif args.mode == 'signals':
            diag.mode_signals(args)
        elif args.mode == 'tesla-ignition':
            diag.mode_tesla_ignition(args)
        elif args.mode == 'dump':
            diag.mode_dump(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        diag.close()


if __name__ == '__main__':
    main()
