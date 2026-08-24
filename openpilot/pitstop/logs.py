import json
import logging
import os
import subprocess

from openpilot.system.hardware.hw import Paths

logger = logging.getLogger("pitstop")


class LogMixin:

  def _read_swaglog(self, limit=500, min_level=0, search=None, proc=None):
    import glob
    log_dir = Paths.swaglog_root()
    pattern = os.path.join(log_dir, 'swaglog.*')
    files = sorted(glob.glob(pattern), reverse=True)
    entries = []
    search_lc = search.lower() if search else None
    proc_lc = proc.lower() if proc else None
    for fpath in files[:15]:
      try:
        with open(fpath, 'r', errors='replace') as f:
          for line in f:
            line = line.strip()
            if not line:
              continue
            try:
              d = json.loads(line)
              levelnum = d.get('levelnum', 20)
              if levelnum < min_level:
                continue
              name = d.get('name', '')
              raw_msg = d.get('msg$s') or d.get('msg', '')
              msg = json.dumps(raw_msg) if isinstance(raw_msg, (dict, list)) else str(raw_msg)
              if proc_lc and proc_lc not in name.lower():
                continue
              if search_lc and search_lc not in msg.lower() and search_lc not in name.lower():
                continue
              if levelnum >= 50: lvlname = 'CRITICAL'
              elif levelnum >= 40: lvlname = 'ERROR'
              elif levelnum >= 30: lvlname = 'WARNING'
              elif levelnum >= 10: lvlname = 'DEBUG' if levelnum < 20 else 'INFO'
              else: lvlname = 'DEBUG'
              entries.append({
                'ts': d.get('created', 0), 'level': (d.get('levelname') or lvlname).upper(),
                'levelnum': levelnum, 'source': 'swaglog', 'process': name,
                'filename': d.get('filename', ''), 'lineno': d.get('lineno', 0), 'msg': msg,
              })
            except Exception:
              pass
      except Exception:
        continue
      if len(entries) >= limit * 3:
        break
    entries.sort(key=lambda x: x['ts'], reverse=True)
    return entries[:limit]

  def _read_journal(self, limit=500, search=None, proc=None, kernel=False):
    cmd = ['journalctl', '-o', 'json', f'-n{limit}', '--no-pager']
    if kernel:
      cmd.append('-k')
    if proc:
      cmd += ['-t', proc]
    try:
      result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
      PRIO_MAP = {0:'CRITICAL',1:'CRITICAL',2:'CRITICAL',3:'ERROR',4:'WARNING',5:'INFO',6:'INFO',7:'DEBUG'}
      PRIO_NUM = {0:50,1:50,2:50,3:40,4:30,5:20,6:20,7:10}
      search_lc = search.lower() if search else None
      entries = []
      for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
          continue
        try:
          d = json.loads(line)
          raw_msg = d.get('MESSAGE', '')
          if isinstance(raw_msg, list):
            msg = ''.join(chr(c) for c in raw_msg if isinstance(c, int) and c < 128)
          else:
            msg = str(raw_msg)
          if search_lc and search_lc not in msg.lower():
            continue
          prio = int(d.get('PRIORITY', 6))
          ts_us = d.get('__REALTIME_TIMESTAMP', '0')
          ts = int(ts_us) / 1_000_000 if ts_us else 0
          identifier = d.get('SYSLOG_IDENTIFIER') or d.get('_COMM', '') or ''
          unit = d.get('_SYSTEMD_UNIT', '')
          process = identifier or unit
          entries.append({
            'ts': ts, 'level': PRIO_MAP.get(prio, 'INFO'),
            'levelnum': PRIO_NUM.get(prio, 20),
            'source': 'kernel' if kernel else 'journal',
            'process': process, 'filename': unit, 'lineno': 0, 'msg': msg,
          })
        except Exception:
          pass
      entries.reverse()
      return entries
    except Exception as e:
      logger.warning(f"journalctl failed: {e}")
      return []

  def _read_crashes(self, limit=30, search=None):
    crash_dir = Paths.crash_log_root()
    entries = []
    search_lc = search.lower() if search else None
    try:
      files = [f for f in os.listdir(crash_dir) if f.endswith('.log') and f != 'error.log']
      files.sort(reverse=True)
      for fname in files[:limit]:
        fpath = os.path.join(crash_dir, fname)
        try:
          stat = os.stat(fpath)
          with open(fpath, 'r', errors='replace') as f:
            content = f.read(32768)
          if search_lc and search_lc not in content.lower():
            continue
          entries.append({
            'ts': stat.st_mtime, 'level': 'ERROR', 'levelnum': 40,
            'source': 'crash', 'process': 'crash', 'filename': fname,
            'lineno': 0, 'msg': content,
          })
        except Exception:
          pass
    except Exception:
      pass
    return entries

  def _read_pitstop(self, limit=500, min_level=0, search=None):
    fpath = "/tmp/pitstop.log"
    entries = []
    search_lc = search.lower() if search else None
    LVL_MAP = {'CRITICAL': 50, 'ERROR': 40, 'WARNING': 30, 'INFO': 20, 'DEBUG': 10}
    try:
      with open(fpath, 'r', errors='replace') as f:
        for line in f:
          line = line.strip()
          if not line:
            continue
          try:
            parts = line.split(' ', 3)
            ts_str = parts[0] + ' ' + parts[1] if len(parts) >= 2 else ''
            rest = parts[3] if len(parts) >= 4 else line
            lvl_str = rest.split(':')[0] if ':' in rest else 'INFO'
            ts = 0
            try:
              from datetime import datetime
              ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").timestamp()
            except Exception:
              pass
            levelnum = LVL_MAP.get(lvl_str.upper(), 20)
            if levelnum < min_level:
              continue
            if search_lc and search_lc not in line.lower():
              continue
            entries.append({
              'ts': ts, 'level': lvl_str.upper(), 'levelnum': levelnum,
              'source': 'pitstop', 'process': 'pitstop', 'filename': '',
              'lineno': 0, 'msg': rest,
            })
          except Exception:
            pass
    except FileNotFoundError:
      pass
    except Exception:
      pass
    entries.sort(key=lambda x: x['ts'], reverse=True)
    return entries[:limit]
