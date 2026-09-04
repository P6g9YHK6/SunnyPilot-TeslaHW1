/* ---------- Utilities ---------- */
function debounce(fn, ms) {
  let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}
function fmtSize(bytes) {
  if (bytes >= 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return bytes + ' B';
}

/* ---------- Navigation ---------- */
let currentPage = 'dashboard';
let autoRefreshTimer = null;
let _webVersion = null;

function toggleNavMenu() {
  document.getElementById('nav-links').classList.toggle('open');
}

function navigateTo(page) {
  document.getElementById('nav-links')?.classList.remove('open');
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`.nav-btn[data-page="${page}"]`)?.classList.add('active');
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page)?.classList.add('active');
  currentPage = page;
  localStorage.setItem('pitstop_last_page', page);
  loadPage(page);
  restartAutoRefresh();
}

document.querySelectorAll('.nav-btn[data-page]').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.page;
    if (currentPage === 'settings' && Object.keys(pendingChanges).length) {
      showModal('Unsaved Changes', '<p>You have unsaved settings changes. Discard them and leave?</p>', [
        { label: 'Stay', action: '', cls: '' },
        { label: 'Discard & Leave', action: `navigateTo('${target}')`, cls: 'btn-danger' },
      ]);
      return;
    }
    navigateTo(target);
  });
});

let _pageLoaded = {};

function loadPage(name, force) {
  if (name !== 'settings') { stopSettingsStatusPoll(); discardPendingChanges(); }
  if (name !== 'dashboard') stopDashboardPoll();
  if (name !== 'models') stopModelsProgressPoll();
  if (name !== 'cockpit') stopCockpitPoll();
  if (name !== 'maps') stopMapProgressPoll();
  if (name === 'dashboard') loadDashboard();
  else if (name === 'backup') {
    _pageLoaded[name] = true;
    loadBackups();
  }
  else if (name === 'vehicle') {
    _pageLoaded[name] = true;
    loadVehicle();
  }
  else if (name === 'maps') {
    _pageLoaded[name] = true;
    loadMaps();
  }
  else if (name === 'cockpit') {
    _pageLoaded[name] = true;
    loadCockpit();
  }
  else if (force || !_pageLoaded[name]) {
    _pageLoaded[name] = true;
    if (name === 'settings') loadSettings();
    else if (name === 'models') loadModels();
    else if (name === 'params') loadParams();
    else if (name === 'logs') loadLogs();
  }
}

function _checkWebVersion(v) {
  if (!v) return;
  if (_webVersion === null) { _webVersion = v; return; }
  if (_webVersion !== v) {
    const banner = document.getElementById('web-version-banner');
    if (banner) banner.style.display = 'block';
  }
}

function fetchAndCheckVersion() {
  api('/api/status', { silent: true }).then(s => _checkWebVersion(s?.webVersion)).catch(() => {});
}

function refreshNow() {
  const btn = document.getElementById('refresh-now-btn');
  btn.classList.add('spinning');
  setTimeout(() => btn.classList.remove('spinning'), 600);
  loadPage(currentPage, true);
}

function setAutoRefresh(seconds) {
  if (seconds === 'custom') {
    const current = localStorage.getItem('pitstop_refresh_v2');
    const curVal = current && current !== '0' ? parseFloat(current) : 5;
    showNumberModal({
      title: 'Custom Refresh Interval',
      value: curVal,
      min: 0.5,
      max: 300,
      step: 0.5,
      suffix: 's',
      onSave: (v) => {
        const sel = document.getElementById('refresh-interval-select');
        if (sel) ensureSelectOption(sel, String(v));
        setAutoRefresh(String(v));
      }
    });
    return;
  }
  clearInterval(autoRefreshTimer);
  autoRefreshTimer = null;
  const s = parseFloat(seconds);
  localStorage.setItem('pitstop_refresh_v2', s);
  if (s > 0) {
    autoRefreshTimer = setInterval(() => {
      if (currentPage === 'settings' && Object.keys(pendingChanges).length > 0) return;
      loadPage(currentPage);
    }, s * 1000);
  }
}

function ensureSelectOption(sel, value) {
  for (let i = 0; i < sel.options.length; i++) {
    if (sel.options[i].value === value) { sel.value = value; return; }
  }
  const opt = document.createElement('option');
  opt.value = value;
  opt.textContent = value + 's';
  sel.appendChild(opt);
  sel.value = value;
}

function restartAutoRefresh() {
  const sel = document.getElementById('refresh-interval-select');
  if (sel) setAutoRefresh(sel.value);
}

function adjFont(delta) {
  let scale = parseFloat(localStorage.getItem('pitstop_font_scale')) || 1;
  scale = Math.round(Math.min(Math.max(scale + delta, 0.7), 1.6) * 100) / 100;
  localStorage.setItem('pitstop_font_scale', scale);
  document.documentElement.style.setProperty('--font-scale', scale);
}

/* ---------- API helper ---------- */
async function api(path, opts = {}) {
  const silent = opts.silent;
  const fetchOpts = { ...opts };
  delete fetchOpts.silent;
  const isFormData = fetchOpts.body instanceof FormData;
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    fetchOpts.signal = controller.signal;
    const res = await fetch(path, {
      headers: { 'Accept': 'application/json', ...(fetchOpts.body && !isFormData ? { 'Content-Type': 'application/json' } : {}) },
      ...fetchOpts,
    });
    clearTimeout(timeout);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `${res.status} ${res.statusText}`);
    }
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) return await res.json();
    return await res.text();
  } catch (e) {
    if (!silent) {
      const isNetError = e.name === 'AbortError'
        || e.message.includes('Failed to fetch')
        || e.message.includes('NetworkError')
        || e.message.includes('TypeError')
        || e.message.includes('network');
      if (isNetError) {
        const ts = new Date().toLocaleTimeString();
        const reason = e.name === 'AbortError' ? 'timeout' : 'unreachable';
        toast(`Error: ${path} @ ${ts} — ${reason}`, 'error');
      } else {
        toast(`Error: ${e.message}`, 'error');
      }
    }
    throw e;
  }
}

/* ---------- Toast ---------- */
function toast(msg, type = 'info') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast ' + type;
  el.classList.remove('hidden');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add('hidden'), 3000);
}

/* ---------- Modal ---------- */
function showModal(title, body, buttons) {
  const html = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal-content">
        <h3>${title}</h3>
        ${body}
        <div class="modal-actions">${(buttons||[]).map(b => `<button class="btn ${b.cls||''} btn-sm" onclick="${b.action ? b.action.replace(/"/g,'&quot;') + ';' : ''}closeModal()">${b.label}</button>`).join('')}</div>
      </div>
    </div>`;
  document.getElementById('modal-container').innerHTML = html;
}

function closeModal() {
  document.getElementById('modal-container').innerHTML = '';
}

/* ---------- Formatting ---------- */
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function fmtBool(v) { return v ? 'Yes' : 'No'; }
function fmtVal(v) {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'boolean') return fmtBool(v);
  return String(v);
}
function fmtRunner(r) {
  const m = {0: 'SNPE', 1: 'Tinygrad', 2: 'Stock'};
  return m[r] || r;
}
function fmtDownloadStatus(s) {
  const m = {0: 'Not Downloading', 1: 'Downloading', 2: 'Downloaded', 3: 'Cached', 4: 'Failed'};
  return m[s] || s;
}
function fmtUpdateStatus(u) {
  const map = {
    checking:        { cls: 'badge-update-progress', label: 'CHECKING' },
    downloading:     { cls: 'badge-update-progress', label: 'DOWNLOADING' },
    finalizing:      { cls: 'badge-update-progress', label: 'FINALIZING' },
    ready:           { cls: 'badge-update-ready',    label: 'READY TO INSTALL' },
    failed:          { cls: 'badge-update-failed',   label: 'FAILED' },
    fetch_available: { cls: 'badge-update-progress', label: 'FETCHING' },
    up_to_date:      { cls: 'badge-update-current',  label: 'UP TO DATE' },
  };
  const s = map[u?.state] || map.up_to_date;
  const busy = ['checking', 'downloading', 'finalizing'].includes(u?.state);
  let detail = '';
  if (u?.state === 'ready' || u?.state === 'fetch_available') detail = u.description;
  else if (u?.state === 'failed') detail = u.last_exception || `${u.failed_count} failed attempt(s)`;
  else if (u?.state === 'up_to_date' && u?.last_update_time) detail = `checked ${new Date(u.last_update_time).toLocaleString()}`;
  const checkBtn = `<button class="btn btn-sm" style="margin-left:0.4rem" onclick="checkForUpdate(this)" ${busy ? 'disabled' : ''}>Check</button>`;
  return `<span class="badge-ign ${s.cls}">${s.label}</span>` +
    (detail ? ` <span style="font-size:0.7rem;color:var(--text-dim)">${escHtml(detail)}</span>` : '') +
    checkBtn;
}

function checkForUpdate(btn) {
  if (btn) btn.disabled = true;
  api('/api/update/check', { method: 'POST' })
    .then(() => toast('Checking for updates…', 'info'))
    .catch(() => { toast('Check failed, updated may not be running', 'error'); if (btn) btn.disabled = false; })
    .finally(() => setTimeout(loadDashboard, 3000));
}

/* ============ DASHBOARD ============ */
function fmtMps(v) {
  if (v === null || v === undefined) return '—';
  return (v * 3.6).toFixed(1) + ' km/h';
}
function fmtPct(v) {
  if (v === null || v === undefined) return '—';
  return v.toFixed(1) + '%';
}
function fmtTemp(v) {
  if (v === null || v === undefined) return '—';
  return v.toFixed(1) + ' °C';
}

function renderTelemetryCard(t) {
  if (!t) { document.getElementById('card-telemetry').querySelector('.card-body').textContent = 'No data'; return; }
  const ign = t.ignition;
  const ignBadge = ign === null
    ? '<span class="badge-ign badge-ign-unknown">—</span>'
    : ign
      ? '<span class="badge-ign badge-ign-on">ON</span>'
      : '<span class="badge-ign badge-ign-off">OFF</span>';
  const car = t.car || {};
  const motion = t.motion || {};
  const standstillBadge = motion.standstill === true ? ' <span class="badge-ign badge-ign-off">STOPPED</span>' : '';
  document.getElementById('card-telemetry').querySelector('.card-body').innerHTML = `
    <div class="row"><span class="label">Ignition</span><span class="value">${ignBadge}</span></div>
    <div class="row"><span class="label">Car</span><span class="value">${car.brand || '—'}</span></div>
    <div class="row"><span class="label">Fingerprint</span><span class="value" style="font-size:0.72rem">${car.fingerprint || '—'}</span></div>
    ${car.vin ? `<div class="row"><span class="label">VIN</span><span class="value" style="font-size:0.72rem">${car.vin}</span></div>` : ''}
    <div class="row"><span class="label">Speed</span><span class="value">${fmtMps(motion.speed_ms)}${standstillBadge}</span></div>
    <div class="row"><span class="label">Gear</span><span class="value">${motion.gear || '—'}</span></div>
  `;
}

function renderSystemCard(t, status) {
  const el = document.getElementById('card-system').querySelector('.card-body');
  if (!t) { el.textContent = 'No data'; return; }
  const dev = t.device || {};
  el.innerHTML = `
    <div class="row"><span class="label">CPU</span><span class="value">${fmtPct(dev.cpu_pct)}</span></div>
    <div class="row"><span class="label">RAM</span><span class="value">${fmtPct(dev.memory_pct)}</span></div>
    <div class="row"><span class="label">Temp</span><span class="value">${fmtTemp(dev.temp_c)}</span></div>
    ${dev.thermal_status ? `<div class="row"><span class="label">Thermal</span><span class="value">${dev.thermal_status}</span></div>` : ''}
    ${status ? `
    <div class="row"><span class="label">Web UI</span><span class="value">${fmtBool(status.enabled)}</span></div>
    <div class="row"><span class="label">Offroad</span><span class="value">${fmtBool(status.is_offroad)}</span></div>
    ` : ''}
    <div class="row" style="margin-top:0.5rem;display:flex;gap:0.4rem;flex-wrap:wrap">
      <button class="btn btn-sm" onclick="restartOpenpilot()">Restart OP</button>
      <button class="btn btn-sm" onclick="restartPitstop()">Restart PitStop</button>
      <button class="btn btn-sm btn-danger" onclick="rebootDevice()">Reboot</button>
    </div>
  `;
}

/* ── Diagnostic card (services / alert / error badge) ── */
function renderDiagCard(d) {
  const body = document.getElementById('card-diag').querySelector('.card-body');
  const badge = document.getElementById('diag-summary-badge');
  if (!d || !d.services) { body.textContent = 'No data'; return; }

  const ok = d.services_ok;
  badge.className = ok ? 'diag-badge diag-ok' : 'diag-badge diag-fail';
  badge.textContent = ok ? 'OK' : 'ISSUES';

  let alertHtml = '';
  if (d.alert && d.alert.text1 && d.alert.type && !d.alert.type.includes('startupNoCar')) {
    const cls = d.alert.status === 'critical' ? 'diag-alert-crit' : 'diag-alert-warn';
    alertHtml = `<div class="diag-alert ${cls}">${escHtml(d.alert.text1)}${d.alert.text2 ? ' — ' + escHtml(d.alert.text2) : ''}</div>`;
  }

  const svcRows = d.services.map(s => {
    const rowCls = !s.alive ? 'diag-row-dead' : (!s.valid || !s.freq_ok) ? 'diag-row-warn' : '';
    const readers = s.readers != null
      ? `<span class="diag-readers${s.readers >= 14 ? ' diag-readers-hi' : ''}">${s.readers}/15</span>` : '';
    return `<div class="diag-row ${rowCls}">
      <span class="diag-svc-name">${s.name}</span>
      <span class="diag-dots">
        <span class="diag-dot ${s.valid?'dot-ok':'dot-fail'}" title="valid">V</span>
        <span class="diag-dot ${s.alive?'dot-ok':'dot-fail'}" title="alive">A</span>
        <span class="diag-dot ${s.freq_ok?'dot-ok':'dot-fail'}" title="freq">F</span>
      </span>
      ${readers}
    </div>`;
  }).join('');

  body.innerHTML = alertHtml + svcRows;
  updateLogsErrorBadge();
}

/* ── Processes card ── */
function renderProcessesCard(d) {
  const el = document.getElementById('card-processes').querySelector('.card-body');
  if (!d || !d.processes) { el.textContent = 'No data'; return; }
  const allProcs = d.processes.sort((a, b) => {
    if (a.running !== b.running) return a.running ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  el.innerHTML = allProcs.map(p => {
    const dotCls = p.running ? 'dot-ok' : 'dot-fail';
    const label = p.running ? 'RUN' : 'DEAD';
    return `<div class="row${p.running ? '' : ' row-dead'}"><span class="label">${escHtml(p.name)}</span><span class="value"><span class="diag-dot ${dotCls}" style="font-size:0.55rem;padding:0 0.3rem">${label}</span></span></div>`;
  }).join('');
}

async function updateLogsErrorBadge() {
  try {
    const entries = await api('/api/logs?source=swaglog&level=40&limit=50', { silent: true });
    const badge = document.getElementById('nav-logs-badge');
    if (!badge) return;
    if (entries && entries.length > 0) {
      badge.textContent = entries.length >= 50 ? '50+' : String(entries.length);
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  } catch (_) {}
}

/* ── New dashboard card renderers ── */
function renderGpsCard(g) {
  const el = document.getElementById('card-gps').querySelector('.card-body');
  if (!g || g.error) { el.innerHTML = '<div class="row"><span class="label">Fix</span><span class="value">No GPS fix</span></div>'; return; }
  el.innerHTML = `
    <div class="row"><span class="label">Fix</span><span class="value">${g.has_fix ? '<span class="diag-dot dot-ok">OK</span>' : '<span class="diag-dot dot-fail">No</span>'}</span></div>
    <div class="row"><span class="label">Lat</span><span class="value">${g.latitude != null ? g.latitude.toFixed(5) : '—'}</span></div>
    <div class="row"><span class="label">Lon</span><span class="value">${g.longitude != null ? g.longitude.toFixed(5) : '—'}</span></div>
    <div class="row"><span class="label">Speed</span><span class="value">${g.speed != null ? fmtMps(g.speed) : '—'}</span></div>
    <div class="row"><span class="label">Bearing</span><span class="value">${g.bearing != null ? g.bearing.toFixed(1) + '°' : '—'}</span></div>
    <div class="row"><span class="label">Altitude</span><span class="value">${g.altitude != null ? g.altitude.toFixed(0) + ' m' : '—'}</span></div>
    <div class="row"><span class="label">Accuracy</span><span class="value">${g.accuracy != null ? g.accuracy.toFixed(1) + ' m' : '—'}</span></div>
    <div class="row"><span class="label">Satellites</span><span class="value">${g.satellites ?? '—'}</span></div>
  `;
}

function renderCalibrationCard(c) {
  const el = document.getElementById('card-calibration').querySelector('.card-body');
  if (!c || c.error) { el.textContent = 'No data'; return; }
  const s = c.status;
  const badge = s === 'calibrated' ? '<span class="diag-dot dot-ok">Calibrated</span>' : s === 'uncalibrated' ? '<span style="color:var(--warn)">Uncalibrated</span>' : s === 'recalibrating' ? '<span style="color:var(--warn)">Recalibrating</span>' : s;
  const pct = c.percent != null ? c.percent : 0;
  el.innerHTML = `
    <div class="row"><span class="label">Status</span><span class="value">${badge}</span></div>
    ${c.percent != null ? `<div class="row"><span class="label">Progress</span><span class="value"><div class="progress-bar" style="width:100%;height:6px"><div class="progress-fill" style="width:${pct}%"></div></div></span></div>` : ''}
    <div class="row"><span class="label">Pitch</span><span class="value">${c.pitch != null ? c.pitch.toFixed(3) + ' rad' : '—'}</span></div>
    <div class="row"><span class="label">Roll</span><span class="value">${c.roll != null ? c.roll.toFixed(3) + ' rad' : '—'}</span></div>
    <div class="row"><span class="label">Yaw</span><span class="value">${c.yaw != null ? c.yaw.toFixed(3) + ' rad' : '—'}</span></div>
    <div class="row"><span class="label">Blocks</span><span class="value">${c.valid_blocks ?? '—'}</span></div>
  `;
}

function renderNetworkCard(n) {
  const el = document.getElementById('card-network').querySelector('.card-body');
  if (!n || !n.type) { el.textContent = 'No data'; return; }

  const sigDot = n.strength === 'great' ? 'dot-ok' : n.strength === 'good' ? 'dot-warn' : 'dot-fail';

  const cloudStr = n.last_athena_ping != null ? `${fmtDuration(n.last_athena_ping)} ago` : 'offline';

  let rows = `
    <div class="row"><span class="label">Type</span><span class="value">${n.type}</span></div>
    <div class="row"><span class="label">Signal</span><span class="value"><span class="diag-dot ${sigDot}" style="font-size:0.55rem;padding:0 0.4rem">${n.strength}</span></span></div>
    <div class="row"><span class="label">Metered</span><span class="value">${n.metered != null ? (n.metered ? 'Yes' : 'No') : '—'}</span></div>
    ${n.tech ? `<div class="row"><span class="label">Technology</span><span class="value">${n.tech}</span></div>` : ''}
    ${n.net_state ? `<div class="row"><span class="label">State</span><span class="value">${n.net_state}</span></div>` : ''}
    ${n.mac ? `<div class="row"><span class="label">MAC</span><span class="value">${n.mac}</span></div>` : ''}
    ${n.device_ip ? `<div class="row"><span class="label">Device IP</span><span class="value">${n.device_ip}</span></div>` : ''}
    ${n.gateway ? `<div class="row"><span class="label">Gateway</span><span class="value">${n.gateway}</span></div>` : ''}
    <div class="row"><span class="label">Cloud</span><span class="value">${cloudStr}</span></div>
  `;
  if (n.wwanTx || n.wwanRx) {
    rows += `
    <div class="row"><span class="label">Tx</span><span class="value">${n.wwanTx != null ? fmtSize(n.wwanTx) : '—'}</span></div>
    <div class="row"><span class="label">Rx</span><span class="value">${n.wwanRx != null ? fmtSize(n.wwanRx) : '—'}</span></div>
    `;
  }

  if (n.hotspot && n.hotspot.active) {
    rows += `
      <div class="diag-section-title" style="margin-top:0.6rem">Hotspot</div>
      <div class="row"><span class="label">Status</span><span class="value"><span class="diag-dot dot-ok" style="font-size:0.55rem;padding:0 0.4rem">ACTIVE</span></span></div>
      <div class="row"><span class="label">SSID</span><span class="value">${n.hotspot.ssid || '—'}</span></div>
      <div class="row"><span class="label">Password</span><span class="value">${n.hotspot.password || '—'}</span></div>
      <div class="row"><span class="label">Gateway</span><span class="value">${n.hotspot.gateway || '—'}</span></div>
      <div class="row"><span class="label">Clients</span><span class="value">${n.hotspot.clients != null ? n.hotspot.clients : '—'}</span></div>
    `;
  }

  el.innerHTML = rows;
}

function renderSunnylinkCard(s) {
  const el = document.getElementById('card-sunnylink').querySelector('.card-body');
  if (!s) { el.textContent = 'No data'; return; }
  const badge = !s.enabled ? '<span class="diag-dot dot-fail" style="padding:2px 6px;font-size:0.65rem">Disabled</span>'
    : s.online ? '<span class="diag-dot dot-ok" style="padding:2px 6px;font-size:0.65rem">Online</span>'
    : '<span class="diag-dot dot-fail" style="padding:2px 6px;font-size:0.65rem">Offline</span>';
  el.innerHTML = `
    <div class="row"><span class="label">Status</span><span class="value">${badge}</span></div>
    <div class="row"><span class="label">Dongle ID</span><span class="value" style="font-size:0.72rem">${s.dongle_id || '—'}</span></div>
    <div class="row"><span class="label">Registered</span><span class="value">${s.registered ? 'Yes' : 'No'}</span></div>
    <div class="row"><span class="label">Temp Fault</span><span class="value">${s.temp_fault ? 'Yes' : 'No'}</span></div>
    <div class="row"><span class="label">Ready</span><span class="value">${s.ready ? '<span class="diag-dot dot-ok">Yes</span>' : '<span class="diag-dot dot-fail">No</span>'}</span></div>
  `;
}

function renderStorageCard(st, telemetry) {
  const el = document.getElementById('card-storage').querySelector('.card-body');
  if (!st) { el.textContent = 'No data'; return; }
  function bar(pct) { return `<div class="progress-bar" style="width:100%;height:5px"><div class="progress-fill" style="width:${Math.min(pct,100)}%"></div></div>`; }
  function fmtGb(b) { return (b / 1073741824).toFixed(1) + ' GB'; }
  function row(label, u) {
    if (!u) return '';
    return `<div class="row"><span class="label">${label}</span><span class="value">${fmtGb(u.used)} / ${fmtGb(u.total)} ${bar(u.pct)}</span></div>`;
  }
  const freePct = telemetry?.device?.free_space_pct != null ? fmtPct(telemetry.device.free_space_pct) : null;
  el.innerHTML = (freePct ? `<div class="row"><span class="label">Free</span><span class="value">${freePct}</span></div>` : '') + row('Internal', st.root) + row('Data', st.data) + row('Logs', st.logs) + row('Models', st.models) + row('Crashes', st.crashes);
}

/* ── Speeds Card ── */
function renderSpeedsCard(s) {
  const el = document.getElementById('card-speeds').querySelector('.card-body');
  if (!s) { el.textContent = 'No data'; return; }
  const kmh = v => v != null ? (v * 3.6).toFixed(2) : '—';
  const ms2 = v => v != null ? v.toFixed(2) : '—';
  const m = v => v != null ? v.toFixed(1) : '—';
  const grid = (fl, fr, rl, rr) => `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
      <span>FL: ${kmh(fl)}</span><span style="text-align:right">FR: ${kmh(fr)}</span>
      <span>RL: ${kmh(rl)}</span><span style="text-align:right">RR: ${kmh(rr)}</span>
    </div>`;
  el.innerHTML = `
    <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Wheel Speeds</div>
    ${s.wheels ? grid(s.wheels.fl, s.wheels.fr, s.wheels.rl, s.wheels.rr) : '<span style="font-size:0.7rem;color:var(--text-dim)">No data</span>'}
    <hr style="margin:4px 0;border-color:var(--border)">
    <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Ego / Cruise</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
      <span>Ego: ${kmh(s.ego?.speed)}</span><span style="text-align:right">Accel: ${ms2(s.ego?.aEgo)} m/s²</span>
      <span>Set: ${kmh(s.cruise?.setSpeed)}</span><span style="text-align:right">Cluster: ${kmh(s.cruise?.clusterSpeed)}</span>
    </div>
    <hr style="margin:4px 0;border-color:var(--border)">
    <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Plan</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
      <span>vTarget: ${kmh(s.plan?.vTarget)}</span><span style="text-align:right">vCruise: ${kmh(s.plan?.vCruise)}</span>
      <span>vMax: ${kmh(s.plan?.vMax)}</span><span style="text-align:right">vCurvature: ${kmh(s.plan?.vCurvature)}</span>
      <span>aTarget: ${ms2(s.plan?.aTarget)}</span><span></span>
    </div>
    <hr style="margin:4px 0;border-color:var(--border)">
    <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Lead</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
      <span>vLead: ${kmh(s.lead?.vLead)}</span><span style="text-align:right">vLeadK: ${kmh(s.lead?.vLeadK)}</span>
      <span>vRel: ${kmh(s.lead?.vRel)}</span><span style="text-align:right">dRel: ${m(s.lead?.dRel)} m</span>
    </div>
  `;
}

/* ── Speed Limits Card ── */
function renderSpeedLimitsCard(s) {
  const el = document.getElementById('card-speed-limits').querySelector('.card-body');
  if (!s) { el.textContent = 'No data'; return; }
  const kmh = v => v != null ? (v * 3.6).toFixed(1) + ' km/h' : '—';
  const m = v => v != null ? v.toFixed(0) + ' m' : '—';
  const yesno = v => v != null ? (v ? 'Yes' : 'No') : '—';
  el.innerHTML = `
    <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Car / Map</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
      <span>Car: ${kmh(s.carSpeedLimit)}</span><span></span>
      <span>Map: ${kmh(s.map?.speedLimit)}</span><span style="text-align:right">Map Valid: ${yesno(s.map?.valid)}</span>
      <span>Ahead: ${kmh(s.map?.speedLimitAhead)}</span><span style="text-align:right">Dist: ${m(s.map?.aheadDist)}</span>
      <span>Ahead Valid: ${yesno(s.map?.aheadValid)}</span><span></span>
    </div>
    <hr style="margin:4px 0;border-color:var(--border)">
    <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Resolver</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
      <span>Limit: ${kmh(s.limit?.speedLimit)}</span><span style="text-align:right">Final: ${kmh(s.limit?.speedLimitFinal)}</span>
      <span>Offset: ${kmh(s.limit?.speedLimitOffset)}</span><span style="text-align:right">Dist: ${m(s.limit?.distToSpeedLimit)}</span>
      <span>Valid: ${yesno(s.limit?.valid)}</span><span></span>
    </div>
    <hr style="margin:4px 0;border-color:var(--border)">
    <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">SP Targets</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
      <span>vTarget: ${kmh(s.planSP?.vTarget)}</span><span style="text-align:right">ICBM: ${kmh(s.icbmVtarget)}</span>
      <span>SCC Vision: ${kmh(s.planSP?.sccVisionVTarget)}</span><span style="text-align:right">SCC Map: ${kmh(s.planSP?.sccMapVTarget)}</span>
      <span>SLA: ${kmh(s.planSP?.speedLimitAssistVTarget)}</span><span></span>
    </div>
  `;
}

/* ── Reset Web UI ── */
function resetWebUI() {
  showModal('Reset Web UI', '<p>Clear all local data (theme, auto-refresh, cached state) and reload the page?</p>', [
    { label: 'Cancel', cls: '' },
    { label: 'Reset', action: 'doResetWebUI()', cls: 'btn-danger' },
  ]);
}

function doResetWebUI() {
  localStorage.clear();
  toast('Local storage cleared. Reloading...', 'info');
  setTimeout(() => location.reload(), 500);
}

function rebootDevice() {
  showModal('Reboot Device', '<p>Reboot the device now?</p>', [
    { label: 'Cancel', cls: '' },
    { label: 'Reboot', action: "api('/api/system/reboot',{method:'POST'}).then(()=>toast('Rebooting…','info'))", cls: 'btn-danger' },
  ]);
}

function restartOpenpilot() {
  showModal('Restart openpilot', '<p>Restart openpilot processes? (onroad cycle, no reboot)</p>', [
    { label: 'Cancel', cls: '' },
    { label: 'Restart', action: "api('/api/system/restart',{method:'POST'}).then(()=>toast('Restarting…','info'))", cls: 'btn-primary' },
  ]);
}

function restartPitstop() {
  showModal('Restart PitStop', '<p>Restart the PitStop web server? (quick restart, no driving impact)</p>', [
    { label: 'Cancel', cls: '' },
    { label: 'Restart', action: "api('/api/system/restart-pitstop',{method:'POST'}).then(()=>toast('Restarting PitStop…','info'))", cls: 'btn-primary' },
  ]);
}

function stopDashboardPoll() {}   // kept for loadPage() call-site compatibility
function stopCockpitPoll() {}     // kept for loadPage() call-site compatibility

/* ============ COCKPIT ============ */
function _ckmph(v) {
  if (v === null || v === undefined) return '—';
  return (v * 3.6).toFixed(1) + ' km/h';
}
function _cms2(v) {
  if (v === null || v === undefined) return '—';
  return v.toFixed(2) + ' m/s²';
}
function _crad(v) {
  if (v === null || v === undefined) return '—';
  return v.toFixed(3) + ' rad';
}
function _cpct(v) {
  if (v === null || v === undefined) return '—';
  return (v * 100).toFixed(0) + '%';
}
function _cyesno(v) {
  return v === true ? 'Yes' : v === false ? 'No' : '—';
}
function _cval(v) {
  if (v === null || v === undefined) return '—';
  return String(v);
}
function _cgrid(rows) {
  return '<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">' + rows.join('') + '</div>';
}

async function loadCockpit() {
  try {
    const [speeds, cockpit] = await Promise.all([
      api('/api/speeds', { silent: true }).catch(() => null),
      api('/api/cockpit', { silent: true }).catch(() => null),
    ]);

    // Speeds card (reuses existing renderers from dashboard, but targets cockpit IDs)
    const sEl = document.getElementById('card-cockpit-speeds');
    if (sEl) {
      if (!speeds) {
        sEl.querySelector('.card-body').textContent = 'No data';
      } else {
        const kmh = v => v != null ? (v * 3.6).toFixed(2) : '—';
        const ms2 = v => v != null ? v.toFixed(2) : '—';
        const m = v => v != null ? v.toFixed(1) : '—';
        const grid = (fl, fr, rl, rr) => `
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
            <span>FL: ${kmh(fl)}</span><span style="text-align:right">FR: ${kmh(fr)}</span>
            <span>RL: ${kmh(rl)}</span><span style="text-align:right">RR: ${kmh(rr)}</span>
          </div>`;
        sEl.querySelector('.card-body').innerHTML = `
          <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Wheel Speeds</div>
          ${speeds.wheels ? grid(speeds.wheels.fl, speeds.wheels.fr, speeds.wheels.rl, speeds.wheels.rr) : '<span style="font-size:0.7rem;color:var(--text-dim)">No data</span>'}
          <hr style="margin:4px 0;border-color:var(--border)">
          <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Ego / Cruise</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
            <span>Ego: ${kmh(speeds.ego?.speed)}</span><span style="text-align:right">Accel: ${ms2(speeds.ego?.aEgo)} m/s²</span>
            <span>Set: ${kmh(speeds.cruise?.setSpeed)}</span><span style="text-align:right">Cluster: ${kmh(speeds.cruise?.clusterSpeed)}</span>
          </div>
          <hr style="margin:4px 0;border-color:var(--border)">
          <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Plan</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
            <span>vTarget: ${kmh(speeds.plan?.vTarget)}</span><span style="text-align:right">vCruise: ${kmh(speeds.plan?.vCruise)}</span>
            <span>vMax: ${kmh(speeds.plan?.vMax)}</span><span style="text-align:right">vCurvature: ${kmh(speeds.plan?.vCurvature)}</span>
            <span>aTarget: ${ms2(speeds.plan?.aTarget)}</span><span></span>
          </div>
          <hr style="margin:4px 0;border-color:var(--border)">
          <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Lead</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
            <span>vLead: ${kmh(speeds.lead?.vLead)}</span><span style="text-align:right">vLeadK: ${kmh(speeds.lead?.vLeadK)}</span>
            <span>vRel: ${kmh(speeds.lead?.vRel)}</span><span style="text-align:right">dRel: ${m(speeds.lead?.dRel)} m</span>
          </div>
        `;
      }
    }

    // Speed Limits card
    const slEl = document.getElementById('card-cockpit-speed-limits');
    if (slEl) {
      if (!speeds) {
        slEl.querySelector('.card-body').textContent = 'No data';
      } else {
        const kmh = v => v != null ? (v * 3.6).toFixed(1) + ' km/h' : '—';
        const m = v => v != null ? v.toFixed(0) + ' m' : '—';
        const yesno = v => v != null ? (v ? 'Yes' : 'No') : '—';
        slEl.querySelector('.card-body').innerHTML = `
          <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Car / Map</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
            <span>Car: ${kmh(speeds.carSpeedLimit)}</span><span></span>
            <span>Map: ${kmh(speeds.map?.speedLimit)}</span><span style="text-align:right">Map Valid: ${yesno(speeds.map?.valid)}</span>
            <span>Ahead: ${kmh(speeds.map?.speedLimitAhead)}</span><span style="text-align:right">Dist: ${m(speeds.map?.aheadDist)}</span>
            <span>Ahead Valid: ${yesno(speeds.map?.aheadValid)}</span><span></span>
          </div>
          <hr style="margin:4px 0;border-color:var(--border)">
          <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Resolver</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
            <span>Limit: ${kmh(speeds.limit?.speedLimit)}</span><span style="text-align:right">Final: ${kmh(speeds.limit?.speedLimitFinal)}</span>
            <span>Offset: ${kmh(speeds.limit?.speedLimitOffset)}</span><span style="text-align:right">Dist: ${m(speeds.limit?.distToSpeedLimit)}</span>
            <span>Valid: ${yesno(speeds.limit?.valid)}</span><span></span>
          </div>
          <hr style="margin:4px 0;border-color:var(--border)">
          <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">SP Targets</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
            <span>vTarget: ${kmh(speeds.planSP?.vTarget)}</span><span style="text-align:right">ICBM: ${kmh(speeds.icbmVtarget)}</span>
            <span>SCC Vision: ${kmh(speeds.planSP?.sccVisionVTarget)}</span><span style="text-align:right">SCC Map: ${kmh(speeds.planSP?.sccMapVTarget)}</span>
            <span>SLA: ${kmh(speeds.planSP?.speedLimitAssistVTarget)}</span><span></span>
          </div>
        `;
      }
    }

    // Live Parameters card
    const pEl = document.getElementById('card-cockpit-params');
    if (pEl) {
      if (!cockpit) {
        pEl.querySelector('.card-body').textContent = 'No data';
      } else {
        const lp = cockpit.liveParameters || {};
        const ltp = cockpit.liveTorqueParameters || {};
        const ld = cockpit.liveDelay || {};
        pEl.querySelector('.card-body').innerHTML = _cgrid([
          '<span>Angle Offset</span><span style="text-align:right">' + _crad(lp.angleOffsetDeg) + '</span>',
          '<span>Stiffness</span><span style="text-align:right">' + _cval(lp.stiffnessFactor) + '</span>',
          '<span>Steer Ratio</span><span style="text-align:right">' + _cval(lp.steerRatio) + '</span>',
          '<span>Sensors Valid</span><span style="text-align:right">' + _cyesno(lp.sensorValid) + '</span>',
          '<span>Posenet Speed</span><span style="text-align:right">' + _ckmph(lp.posenetSpeed) + '</span>',
          '<hr style="margin:4px 0;border-color:var(--border);grid-column:1/-1">',
          '<span>Lat Accel Factor</span><span style="text-align:right">' + _cval(ltp.latAccelFactorFiltered) + '</span>',
          '<span>Friction Coeff</span><span style="text-align:right">' + _cval(ltp.frictionCoefficientFiltered) + '</span>',
          '<hr style="margin:4px 0;border-color:var(--border);grid-column:1/-1">',
          '<span>Lateral Delay</span><span style="text-align:right">' + (ld.lateralDelay != null ? ld.lateralDelay.toFixed(2) + ' s' : '—') + '</span>',
          '<span>Delay Status</span><span style="text-align:right">' + _cval(ld.status) + '</span>',
        ]);
      }
    }

    // Pose / Velocity card
    const poseEl = document.getElementById('card-cockpit-pose');
    if (poseEl) {
      if (!cockpit) {
        poseEl.querySelector('.card-body').textContent = 'No data';
      } else {
        const pose = cockpit.livePose || {};
        const vel = pose.velocityDevice || {};
        const acc = pose.accelerationDevice || {};
        const velMag = (vel.x != null && vel.y != null && vel.z != null)
          ? Math.sqrt(vel.x*vel.x + vel.y*vel.y + vel.z*vel.z).toFixed(2) + ' m/s'
          : '—';
        poseEl.querySelector('.card-body').innerHTML = `
          <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Device Velocity</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
            <span>X: ${_cval(vel.x)}</span><span style="text-align:right">Y: ${_cval(vel.y)}</span>
            <span>Z: ${_cval(vel.z)}</span><span style="text-align:right">Mag: ${velMag}</span>
          </div>
          <hr style="margin:4px 0;border-color:var(--border)">
          <div style="font-size:0.75rem;font-weight:600;margin-bottom:3px">Device Acceleration</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:0.75rem">
            <span>X: ${_cms2(acc.x)}</span><span style="text-align:right">Y: ${_cms2(acc.y)}</span>
            <span>Z: ${_cms2(acc.z)}</span><span></span>
          </div>
        `;
      }
    }

    // Driver card
    const dEl = document.getElementById('card-cockpit-driver');
    if (dEl) {
      if (!cockpit) {
        dEl.querySelector('.card-body').textContent = 'No data';
      } else {
        const dms = cockpit.driverMonitoringState || {};
        dEl.querySelector('.card-body').innerHTML = _cgrid([
          '<span>Awareness</span><span style="text-align:right">' + _cpct(dms.awarenessPercent) + '</span>',
          '<span>Face Detected</span><span style="text-align:right">' + _cyesno(dms.faceDetected) + '</span>',
          '<span>Distracted</span><span style="text-align:right">' + _cyesno(dms.isDistracted) + '</span>',
          '<span>Wheel Side</span><span style="text-align:right">' + _cval(dms.wheelSide) + '</span>',
          '<span>Alert</span><span style="text-align:right">' + _cval(dms.alertStatus) + '</span>',
          '<span>Alert Type</span><span style="text-align:right">' + _cval(dms.alertType) + '</span>',
        ]);
      }
    }

    // System State card
    const stEl = document.getElementById('card-cockpit-state');
    if (stEl) {
      if (!cockpit) {
        stEl.querySelector('.card-body').textContent = 'No data';
      } else {
        const sds = cockpit.selfdriveState || {};
        const cal = cockpit.calibration || {};
        const calBadge = cal.status === 'calibrated'
          ? '<span class="diag-dot dot-ok">Calibrated</span>'
          : '<span style="color:var(--warn)">' + _cval(cal.status) + '</span>';
        const enBadge = sds.enabled
          ? '<span class="diag-dot dot-ok">ON</span>'
          : '<span class="diag-dot dot-fail">OFF</span>';
        stEl.querySelector('.card-body').innerHTML = _cgrid([
          '<span>Enabled</span><span style="text-align:right">' + enBadge + '</span>',
          '<span>Active</span><span style="text-align:right">' + _cyesno(sds.active) + '</span>',
          '<span>State</span><span style="text-align:right">' + _cval(sds.state) + '</span>',
          '<span>Experimental</span><span style="text-align:right">' + _cyesno(sds.experimentalMode) + '</span>',
          '<hr style="margin:4px 0;border-color:var(--border);grid-column:1/-1">',
          '<span>Calibration</span><span style="text-align:right">' + calBadge + '</span>',
          '<span>Cal %</span><span style="text-align:right">' + (cal.percent != null ? cal.percent.toFixed(0) + '%' : '—') + '</span>',
        ]);
      }
    }
  } catch (e) {
    document.querySelectorAll('#card-cockpit-speeds .card-body, #card-cockpit-speed-limits .card-body, #card-cockpit-params .card-body, #card-cockpit-pose .card-body, #card-cockpit-driver .card-body, #card-cockpit-state .card-body')
      .forEach(el => el.textContent = 'Failed to load.');
  }
}

async function loadDashboard() {
  try {
    const [device, caps, status, activeModel, telemetry, diag, updateStatus, gps, calibration, network, sunnylink, storage] = await Promise.all([
      api('/api/device'),
      api('/api/capabilities'),
      api('/api/status'),
      api('/api/models/active'),
      api('/api/telemetry', { silent: true }).catch(() => null),
      api('/api/diag', { silent: true }).catch(() => null),
      api('/api/update', { silent: true }).catch(() => null),
      api('/api/gps', { silent: true }).catch(() => null),
      api('/api/calibration', { silent: true }).catch(() => null),
      api('/api/network', { silent: true }).catch(() => null),
      api('/api/sunnylink', { silent: true }).catch(() => null),
      api('/api/storage', { silent: true }).catch(() => null),
    ]);

    _checkWebVersion(status?.webVersion);

    document.getElementById('card-device').querySelector('.card-body').innerHTML = `
      <div class="row"><span class="label">Dongle ID</span><span class="value">${device.dongle_id || '—'}</span></div>
      <div class="row"><span class="label">Serial</span><span class="value">${device.hardware_serial || '—'}</span></div>
      <div class="row"><span class="label">Version</span><span class="value">${device.version || '—'}</span></div>
      <div class="row"><span class="label">Branch</span><span class="value">${device.branch || '—'}</span></div>
      <div class="row"><span class="label">Repo</span><span class="value" style="font-size:0.72rem">${device.git_repo || '—'}</span></div>
      <div class="row"><span class="label">Commit</span><span class="value">${device.git_commit ? device.git_commit.slice(0, 8) : '—'}</span></div>
      <div class="row"><span class="label">Date</span><span class="value" style="font-size:0.72rem">${device.git_commit_date ? device.git_commit_date.split(' ').slice(0, 2).join(' ') : '—'}</span></div>
      <div class="row"><span class="label">Dirty</span><span class="value">${fmtBool(device.is_dirty)}</span></div>
      <div class="row"><span class="label">Update</span><span class="value">${fmtUpdateStatus(updateStatus)}</span></div>
    `;

    document.getElementById('card-capabilities').querySelector('.card-body').innerHTML = `
      <div class="row"><span class="label">Brand</span><span class="value">${caps.brand || '—'}</span></div>
      <div class="row"><span class="label">Device Type</span><span class="value">${caps.device_type || '—'}</span></div>
      <div class="row"><span class="label">Longitudinal</span><span class="value">${fmtBool(caps.has_longitudinal_control)}</span></div>
      <div class="row"><span class="label">Torque Allowed</span><span class="value">${fmtBool(caps.torque_allowed)}</span></div>
      <div class="row"><span class="label">Steer Type</span><span class="value">${caps.steer_control_type || '—'}</span></div>
      <div class="row"><span class="label">ICBM</span><span class="value">${fmtBool(caps.has_icbm)}</span></div>
    `;

    document.getElementById('card-model').querySelector('.card-body').innerHTML = `
      <div class="row"><span class="label">Model</span><span class="value">${activeModel.displayName || activeModel.internalName || '—'}</span></div>
      <div class="row"><span class="label">Runner</span><span class="value">${activeModel.runner !== undefined ? fmtRunner(activeModel.runner) : 'Stock'}</span></div>
      <div class="row"><span class="label">Generation</span><span class="value">${activeModel.generation ?? '—'}</span></div>
      <div class="row"><span class="label">Environment</span><span class="value">${activeModel.environment || '—'}</span></div>
      <div class="row"><span class="label">20 Hz</span><span class="value">${activeModel.is20hz !== undefined ? fmtBool(activeModel.is20hz) : '—'}</span></div>
    `;

    renderTelemetryCard(telemetry);
    renderSystemCard(telemetry, status);
    renderDiagCard(diag);
    renderProcessesCard(diag);
    renderGpsCard(gps);
    renderCalibrationCard(calibration);
    renderNetworkCard(network);
    renderSunnylinkCard(sunnylink);
    renderStorageCard(storage, telemetry);
  } catch (e) {
    document.querySelectorAll('#card-device .card-body, #card-capabilities .card-body, #card-model .card-body')
      .forEach(el => el.textContent = 'Failed to load.');
  }
}

/* ============ SETTINGS WITH RULE ENGINE ============ */
let settingsSchema = null;
let settingsCapabilities = {};
let settingsParamCache = {};
let settingsStatus = { is_offroad: true, is_metric: false };
let reEvalPending = false;
let settingsStatusInterval = null;
let settingsSearchQuery = '';
let settingsFavorites = [];

/* ---- Pending changes queue ---- */
let pendingChanges = {};
// shape: { [key]: { oldValue, newValue, label, needsCycle } }

function fmtDuration(seconds) {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

function fmtPendingVal(v) {
  if (v === null || v === undefined) return '—';
  if (v === '1' || v === true) return 'On';
  if (v === '0' || v === false) return 'Off';
  return String(v);
}

function renderPendingBar() {
  const bar = document.getElementById('pending-bar');
  const entries = Object.entries(pendingChanges);
  if (!entries.length) { bar.classList.add('hidden'); return; }

  const cycleCount = entries.filter(([, e]) => e.needsCycle).length;
  const warningHtml = cycleCount
    ? `<span class="pending-warn">&#9888; ${cycleCount} require${cycleCount === 1 ? 's' : ''} a drive cycle</span>`
    : '';

  const listHtml = entries.map(([key, e]) =>
    `<span class="pending-entry">${e.label || key}: <b>${fmtPendingVal(e.oldValue)}</b> &#8594; <b>${fmtPendingVal(e.newValue)}</b></span>`
  ).join('');

  bar.innerHTML = `
    <div class="pending-summary">
      <span class="pending-count">${entries.length} unsaved change${entries.length !== 1 ? 's' : ''}</span>
      ${warningHtml}
      <div class="pending-list">${listHtml}</div>
    </div>
    <div class="pending-actions">
      <button class="btn btn-sm" onclick="discardPendingChanges()">Discard</button>
      <button class="btn btn-sm btn-primary" onclick="applyPendingChanges()">Apply</button>
    </div>
  `;
  bar.classList.remove('hidden');
}

async function applyPendingChanges() {
  const entries = Object.entries(pendingChanges);
  if (!entries.length) return;
  const results = await Promise.allSettled(entries.map(async ([key, e]) => {
    await api(`/api/params/${key}`, { method: 'POST', body: JSON.stringify({ value: e.newValue }) });
    return key;
  }));
  const failed = results.filter(r => r.status === 'rejected').length;
  const succeeded = results.filter(r => r.status === 'fulfilled');
  succeeded.forEach(r => {
    const change = pendingChanges[r.value];
    if (change) settingsParamCache[r.value] = change.newValue;
    delete pendingChanges[r.value];
  });
  if (failed) {
    toast(`${failed} setting${failed !== 1 ? 's' : ''} failed to save`, 'error');
  } else {
    toast(`${entries.length} setting${entries.length !== 1 ? 's' : ''} saved`, 'success');
  }
  renderPendingBar();
  maybeReEval();
}

function discardPendingChanges() {
  Object.entries(pendingChanges).forEach(([key, e]) => {
    settingsParamCache[key] = e.oldValue;
  });
  pendingChanges = {};
  renderPendingBar();
  maybeReEval();
}

function queueChange(key, newValue, label, needsCycle) {
  if (!(key in pendingChanges)) {
    pendingChanges[key] = { oldValue: settingsParamCache[key], newValue, label, needsCycle: !!needsCycle };
  } else {
    pendingChanges[key].newValue = newValue;
    pendingChanges[key].needsCycle = !!needsCycle;
  }
  settingsParamCache[key] = newValue;
  renderPendingBar();
  maybeReEval();
}

/* ---- Rule evaluator ---- */
function evaluateRule(rule, caps, paramCache, status) {
  const t = rule.type;
  if (t === 'offroad_only') return !!status.is_offroad;
  if (t === 'not_engaged') return !status.engaged;
  if (t === 'capability') return caps[rule.field] === rule.equals;
  if (t === 'param') {
    const v = paramCache[rule.key];
    const eq = rule.equals;
    if (eq === true || eq === 'true') return v === '1' || v === 'true' || v === true;
    if (eq === false || eq === 'false') return v === '0' || v === 'false' || v === false;
    return String(v) === String(eq);
  }
  if (t === 'param_compare') {
    const n = parseFloat(paramCache[rule.key]);
    if (isNaN(n)) return false;
    if (rule.op === '>') return n > rule.value;
    if (rule.op === '<') return n < rule.value;
    if (rule.op === '>=') return n >= rule.value;
    if (rule.op === '<=') return n <= rule.value;
    return false;
  }
  if (t === 'not') return !evaluateRule(rule.condition, caps, paramCache, status);
  if (t === 'any') return (rule.conditions || []).some(c => evaluateRule(c, caps, paramCache, status));
  if (t === 'all') return (rule.conditions || []).every(c => evaluateRule(c, caps, paramCache, status));
  return true;
}

function evaluateRules(rules, caps, paramCache, status) {
  if (!rules || !rules.length) return true;
  return rules.every(r => evaluateRule(r, caps, paramCache, status));
}

function hasOffroadOnly(rules) {
  if (!rules || !rules.length) return false;
  return rules.some(r => {
    if (r.type === 'offroad_only') return true;
    if (r.condition) return hasOffroadOnly([r.condition]);
    if (r.conditions) return hasOffroadOnly(r.conditions);
    return false;
  });
}

function getDisabledReason(item, caps, paramCache, status, forceDisabled) {
  if (item.blocked) return 'Can only be changed on the device itself';
  if (forceDisabled) return 'Not supported in this vehicle configuration';
  const rules = item.enablement || [];
  for (const r of rules) {
    if (evaluateRule(r, caps, paramCache, status)) continue;
    const reason = explainRule(r, caps, paramCache, status);
    if (reason) return reason;
  }
  return '';
}

function explainRule(rule, caps, paramCache, status) {
  if (rule.type === 'offroad_only') return 'Requires offroad mode';
  if (rule.type === 'not_engaged') return 'Cannot change while driving';
  if (rule.type === 'capability') return `Requires: ${rule.field}`;
  if (rule.type === 'param') {
    const eq = rule.equals;
    if (eq === true || eq === 'true') return `Requires: ${rule.key}`;
    if (eq === false || eq === 'false') return `Requires: ${rule.key} off`;
    return `Requires: ${rule.key} = ${eq}`;
  }
  if (rule.type === 'param_compare') return `Requires: ${rule.key} ${rule.op} ${rule.value}`;
  if (rule.type === 'not') {
    const inner = explainRule(rule.condition, caps, paramCache, status);
    if (inner) return `Requires: not (${inner.replace(/^Requires:\s*/i, '')})`;
    return '';
  }
  if (rule.type === 'any') {
    const reasons = rule.conditions.map(c => {
      if (evaluateRule(c, caps, paramCache, status)) return null;
      return explainRule(c, caps, paramCache, status);
    }).filter(Boolean);
    if (reasons.length === 1) return reasons[0];
    if (reasons.length > 1) return `Requires: ${reasons.join(' or ')}`;
    return '';
  }
  if (rule.type === 'all') {
    for (const c of rule.conditions) {
      if (!evaluateRule(c, caps, paramCache, status)) {
        const inner = explainRule(c, caps, paramCache, status);
        if (inner) return inner;
      }
    }
    return '';
  }
  return '';
}

/* ---- Number selector modal ---- */
let _nmKey = null, _nmVal = 0, _nmMin = -Infinity, _nmMax = Infinity, _nmStep = 1;
let _nmLabel = '', _nmNeedsCycle = false;

function openNumModal(key, val, min, max, step, label, needsCycle) {
  _nmKey = key;
  _nmVal = parseFloat(val) || 0;
  _nmMin = min !== '' && min !== undefined ? parseFloat(min) : -Infinity;
  _nmMax = max !== '' && max !== undefined ? parseFloat(max) : Infinity;
  _nmStep = parseFloat(step) || 1;
  _nmLabel = label;
  _nmNeedsCycle = !!needsCycle;

  const precision = String(_nmStep).includes('.') ? String(_nmStep).split('.')[1].length : 0;
  const fmtD = v => parseFloat(v.toFixed(precision));
  const d1 = fmtD(_nmStep), d10 = fmtD(_nmStep * 10);
  const minAttr = isFinite(_nmMin) ? `min="${_nmMin}"` : '';
  const maxAttr = isFinite(_nmMax) ? `max="${_nmMax}"` : '';

  const body = `
    <div class="num-modal">
      <input type="number" id="nm-input" class="num-input" value="${_nmVal}" step="${_nmStep}" ${minAttr} ${maxAttr} oninput="nmInputChange(this.value)">
      <div class="num-btns">
        <button class="btn btn-sm" onclick="nmStep(-10)">&#8722;${d10}</button>
        <button class="btn btn-sm" onclick="nmStep(-1)">&#8722;${d1}</button>
        <button class="btn btn-sm" onclick="nmStep(1)">+${d1}</button>
        <button class="btn btn-sm" onclick="nmStep(10)">+${d10}</button>
      </div>
    </div>`;

  showModal(label, body, [
    { label: 'Cancel', action: '', cls: '' },
    { label: 'OK', action: 'nmConfirm()', cls: 'btn-primary' },
  ]);
  setTimeout(() => document.getElementById('nm-input')?.select(), 50);
}

function nmInputChange(v) {
  const p = String(_nmStep).includes('.') ? String(_nmStep).split('.')[1].length : 0;
  _nmVal = parseFloat(parseFloat(v).toFixed(p)) || 0;
}

function nmStep(n) {
  const precision = String(_nmStep).includes('.') ? String(_nmStep).split('.')[1].length : 0;
  _nmVal = parseFloat(Math.min(_nmMax, Math.max(_nmMin, _nmVal + n * _nmStep)).toFixed(precision));
  const inp = document.getElementById('nm-input');
  if (inp) inp.value = _nmVal;
}

function nmConfirm() {
  if (_nmKey) {
    queueChange(_nmKey, String(_nmVal), _nmLabel, _nmNeedsCycle);
  }
}

/* ---- Calibrate (camera offset) modal ---- */
let _calibKey = null, _calibSide = 'left', _calibCm = 0;
let _calibMin = -Infinity, _calibMax = Infinity, _calibStep = 0.01;
let _calibLabel = '', _calibNeedsCycle = false;

function openCalibrateModal(key, val, min, max, step, label, needsCycle) {
  _calibKey = key;
  _calibMin = min !== '' && min !== undefined ? parseFloat(min) : -Infinity;
  _calibMax = max !== '' && max !== undefined ? parseFloat(max) : Infinity;
  _calibStep = parseFloat(step) || 0.01;
  _calibLabel = label;
  _calibNeedsCycle = !!needsCycle;

  const v = parseFloat(val) || 0;
  _calibSide = v < 0 ? 'right' : 'left';
  _calibCm = Math.round(Math.abs(v) * 100);

  _calibRenderStep1();
}

function _calibRenderStep1() {
  const body = `
    <p>Is the device mounted to the left or right of center on the windshield?</p>
    <div class="calib-side-choice">
      <button class="calib-side-btn ${_calibSide === 'left' ? 'active' : ''}" onclick="_calibPickSide('left')">&#8592; Left</button>
      <button class="calib-side-btn ${_calibSide === 'right' ? 'active' : ''}" onclick="_calibPickSide('right')">Right &#8594;</button>
    </div>`;
  showModal(_calibLabel, body, [
    { label: 'Cancel', action: '', cls: '' },
  ]);
}

function _calibPickSide(side) {
  _calibSide = side;
  _calibRenderStep2();
}

function _calibRenderStep2() {
  const maxCm = Math.round(Math.max(Math.abs(_calibMin), Math.abs(_calibMax)) * 100);
  const body = `
    <button class="btn btn-sm calib-back-btn" type="button" onclick="_calibRenderStep1()">&#8592; Back</button>
    <p>How far off center is it, in centimeters?</p>
    <div class="num-modal">
      <input type="number" id="calib-input" class="num-input" value="${_calibCm}" step="1" min="0" max="${maxCm}" oninput="_calibInputChange(this.value)">
      <div class="num-btns">
        <button class="btn btn-sm" onclick="_calibNudge(-10)">&#8722;10</button>
        <button class="btn btn-sm" onclick="_calibNudge(-1)">&#8722;1</button>
        <button class="btn btn-sm" onclick="_calibNudge(1)">+1</button>
        <button class="btn btn-sm" onclick="_calibNudge(10)">+10</button>
      </div>
    </div>`;
  showModal(_calibLabel, body, [
    { label: 'Cancel', action: '', cls: '' },
    { label: 'Confirm', action: '_calibConfirm()', cls: 'btn-primary' },
  ]);
  setTimeout(() => document.getElementById('calib-input')?.select(), 50);
}

function _calibInputChange(v) {
  _calibCm = Math.max(0, Math.round(parseFloat(v) || 0));
}

function _calibNudge(n) {
  _calibCm = Math.max(0, _calibCm + n);
  const inp = document.getElementById('calib-input');
  if (inp) inp.value = _calibCm;
}

function _calibConfirm() {
  if (!_calibKey) return;
  let meters = (_calibSide === 'left' ? 1 : -1) * (_calibCm / 100);
  meters = Math.min(_calibMax, Math.max(_calibMin, meters));
  meters = Math.round(meters / _calibStep) * _calibStep;
  meters = parseFloat(meters.toFixed(2));
  queueChange(_calibKey, String(meters), _calibLabel, _calibNeedsCycle);
}

/* ---- Generic number selector modal (with callback) ---- */
let _nmCallback = null;
let _nmCbVal = 0, _nmCbMin = -Infinity, _nmCbMax = Infinity, _nmCbStep = 1;
let _nmCbSuffix = '';

function showNumberModal({title, value, min, max, step, suffix, onSave}) {
  _nmCallback = onSave;
  _nmCbVal = parseFloat(value) || 0;
  _nmCbMin = min !== undefined ? parseFloat(min) : -Infinity;
  _nmCbMax = max !== undefined ? parseFloat(max) : Infinity;
  _nmCbStep = parseFloat(step) || 1;
  _nmCbSuffix = suffix || '';

  const precision = String(_nmCbStep).includes('.') ? String(_nmCbStep).split('.')[1].length : 0;
  const fmtD = v => parseFloat(v.toFixed(precision));
  const d1 = fmtD(_nmCbStep), d10 = fmtD(_nmCbStep * 10);
  const minAttr = isFinite(_nmCbMin) ? `min="${_nmCbMin}"` : '';
  const maxAttr = isFinite(_nmCbMax) ? `max="${_nmCbMax}"` : '';

  const body = `
    <div class="num-modal">
      <input type="number" id="nmc-input" class="num-input" value="${_nmCbVal}" step="${_nmCbStep}" ${minAttr} ${maxAttr} oninput="nmcInputChange(this.value)">
      <div class="num-btns">
        <button class="btn btn-sm" onclick="nmcStep(-10)">&#8722;${d10}</button>
        <button class="btn btn-sm" onclick="nmcStep(-1)">&#8722;${d1}</button>
        <button class="btn btn-sm" onclick="nmcStep(1)">+${d1}</button>
        <button class="btn btn-sm" onclick="nmcStep(10)">+${d10}</button>
      </div>
    </div>`;

  showModal(title, body, [
    { label: 'Cancel', action: '', cls: '' },
    { label: 'OK', action: 'nmcConfirm()', cls: 'btn-primary' },
  ]);
  setTimeout(() => document.getElementById('nmc-input')?.select(), 50);
}

function nmcInputChange(v) {
  const p = String(_nmCbStep).includes('.') ? String(_nmCbStep).split('.')[1].length : 0;
  _nmCbVal = parseFloat(parseFloat(v).toFixed(p)) || 0;
}

function nmcStep(n) {
  const precision = String(_nmCbStep).includes('.') ? String(_nmCbStep).split('.')[1].length : 0;
  _nmCbVal = parseFloat(Math.min(_nmCbMax, Math.max(_nmCbMin, _nmCbVal + n * _nmCbStep)).toFixed(precision));
  const inp = document.getElementById('nmc-input');
  if (inp) inp.value = _nmCbVal;
}

function nmcConfirm() {
  if (_nmCallback) _nmCallback(_nmCbVal);
  _nmCallback = null;
}

/* ---- Build title with suffix ---- */
function buildTitle(item, paramCache) {
  let t = item.title || item.key || '';
  if (item.title_param_suffix) {
    const suffixCfg = item.title_param_suffix;
    const sv = paramCache[suffixCfg.param];
    const suffix = suffixCfg.values ? suffixCfg.values[sv] : '';
    if (suffix) t += ' ' + suffix;
  }
  return t;
}

/* ---- Build unit label ---- */
function buildUnit(item, isMetric) {
  if (!item.unit) return '';
  if (typeof item.unit === 'string') return ' ' + item.unit;
  return ' ' + (isMetric ? item.unit.metric : item.unit.imperial);
}

/* Client-side widget overrides — force specific keys to use a friendlier
   custom editor without modifying the shared settings schema. */
const WIDGET_OVERRIDES = {
  CameraOffset: {
    widget: 'calibrate',
    title: 'Calibrate Camera Position',
    description: "Tell the device which side of center it's mounted on and how far off, so it can correct what it thinks is straight ahead.",
  },
};

/* ---- Render a single setting item ---- */
let _descId = 0;
function renderSettingItem(item, caps, paramCache, status, depth, forceDisabled = false) {
  const key = item.key || '';
  const override = WIDGET_OVERRIDES[key];
  const title = override?.title || buildTitle(item, paramCache);
  const desc = override?.description || item.description || '';
  const widget = override?.widget || item.widget || 'toggle';
  const needsCycle   = item.needs_onroad_cycle ? '<span class="badge-restart">Restart</span>' : '';
  const offroadOnly  = hasOffroadOnly(item.enablement) ? '<span class="badge-offroad">Offroad</span>' : '';
  const isBlocked    = !!item.blocked;
  const blockedBadge = isBlocked ? '<span class="badge-blocked" title="This setting can only be changed on the device itself">Device only</span>' : '';
  const needsAttest  = !!item.requires_attestation;
  const vis = evaluateRules(item.visibility, caps, paramCache, status);
  const enabled = !isBlocked && !forceDisabled && evaluateRules(item.enablement, caps, paramCache, status);
  const parentChecked = paramCache[key];

  if (!vis) return '';

  let controlHtml = '';
  const idAttr = `si-${key}`;

  if (widget === 'toggle') {
    const sv = String(parentChecked || '');
    const checked = sv === '1' || sv.toLowerCase() === 'true';
    controlHtml = `<label class="toggle">
      <input type="checkbox" id="${idAttr}" data-param="${key}" data-attestation="${needsAttest ? '1' : ''}" ${checked ? 'checked' : ''} ${!enabled ? 'disabled' : ''}>
      <span class="slider"></span>
    </label>`;

  } else if (widget === 'multiple_button' || widget === 'option') {
    /* Always render as <select> — cleaner on portrait and desktop alike */
    const opts = item.options || [];
    const currentVal = String(paramCache[key] ?? '');
    if (opts.length) {
      controlHtml = `<select class="setting-select" data-param="${key}" data-widget="${widget}" data-attestation="${needsAttest ? '1' : ''}" ${!enabled ? 'disabled' : ''}>`;
      opts.forEach(o => {
        const optEnabled = enabled && (widget === 'option' || evaluateRules(o.enablement, caps, paramCache, status));
        controlHtml += `<option value="${o.value}" ${currentVal === String(o.value) ? 'selected' : ''} ${!optEnabled ? 'disabled' : ''}>${o.label}</option>`;
      });
      controlHtml += `</select>`;
    } else if (item.min !== undefined || item.max !== undefined) {
      /* Numeric option — stepper button */
      const unit = buildUnit(item, status.is_metric);
      const safeTitle = title.replace(/'/g, "\\'");
      controlHtml = `<button class="num-edit-btn" data-param="${key}"
        data-min="${item.min ?? ''}" data-max="${item.max ?? ''}" data-step="${item.step ?? 1}"
        data-label="${safeTitle}" data-needs-cycle="${item.needs_onroad_cycle ? '1' : ''}"
        ${!enabled ? 'disabled' : ''}>${fmtVal(paramCache[key])}${unit}</button>`;
    } else {
      /* option widget with no predefined choices and no range = display only */
      const unit = buildUnit(item, status.is_metric);
      controlHtml = `<span class="item-value-mono">${fmtVal(paramCache[key])}${unit}</span>`;
    }

  } else if (widget === 'calibrate') {
    const v = parseFloat(paramCache[key]) || 0;
    const cm = Math.round(Math.abs(v) * 100);
    const sideLabel = cm === 0 ? 'Centered' : (v > 0 ? `${cm}cm left` : `${cm}cm right`);
    controlHtml = `<button class="calibrate-btn" data-param="${key}"
      data-min="${item.min ?? ''}" data-max="${item.max ?? ''}" data-step="${item.step ?? 1}"
      data-label="${title.replace(/'/g, "\\'")}" data-needs-cycle="${item.needs_onroad_cycle ? '1' : ''}"
      ${!enabled ? 'disabled' : ''}>${sideLabel}</button>`;

  } else if (widget === 'info') {
    controlHtml = `<span class="info-display">${fmtVal(paramCache[key])}</span>`;

  } else if (widget === 'button') {
    controlHtml = `<button class="action-btn" data-param="${key}" ${!enabled ? 'disabled' : ''}>${item.action || title}</button>`;

  } else {
    controlHtml = `<span class="item-value-mono">${fmtVal(paramCache[key])}</span>`;
  }

  const disabledReason = (!enabled || isBlocked) ? getDisabledReason(item, caps, paramCache, status, forceDisabled) : '';
  const extraClasses = `${!enabled && !isBlocked ? 'disabled' : ''} ${isBlocked ? 'blocked' : ''}`;
  const reasonBadge = (disabledReason && !isBlocked && !hasOffroadOnly(item.enablement || []))
    ? `<span class="badge-reason">${escHtml(disabledReason)}</span>` : '';
  const indentStyle = depth > 0 ? ` style="padding-left:${1.25 + depth * 1.25}rem"` : '';

  /* Collapsible description: show first 100 chars, expand on click */
  let descHtml = '';
  if (desc) {
    const stripped = desc.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    const did = `desc-${key || (_descId++)}`;
    if (stripped.length > 120) {
      descHtml = `<div class="item-desc" id="${did}">
        <span class="desc-short">${stripped.slice(0, 120).trim()}… <button class="desc-expand" onclick="expandDesc('${did}')">more</button></span>
        <span class="desc-full hidden">${desc} <button class="desc-expand" onclick="collapseDesc('${did}')">less</button></span>
      </div>`;
    } else {
      descHtml = `<div class="item-desc">${desc}</div>`;
    }
  }

  /* Details popover (from item.details field) */
  let detailBtn = '';
  if (item.details) {
    const safeTitle = title.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
    const safeDetails = item.details.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/</g, '&lt;').replace(/>/g, '&gt;');
    detailBtn = `<button class="item-detail-btn" onclick="showModal('${safeTitle}','<p>${safeDetails}</p>',[{label:'Close',action:'',cls:'btn-primary'}])" title="More info">i</button>`;
  }

  const isFav = key && settingsFavorites.includes(key);
  const favBtn = key ? `<button class="fav-btn ${isFav ? 'active' : ''}" onclick="toggleSettingsFav('${key}', this)" title="Favorite">${isFav ? '★' : '☆'}</button>` : '';

  let html = `<div class="section-item ${extraClasses}"${indentStyle}>`;
  html += `<div class="item-info"><div class="item-title">${title}${favBtn}${detailBtn}${needsCycle}${offroadOnly}${blockedBadge}${reasonBadge}</div>${descHtml}</div>`;
  html += `<div class="item-control">${controlHtml}</div>`;
  html += `</div>`;

  return html;
}

function expandDesc(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.querySelector('.desc-short').classList.add('hidden');
  el.querySelector('.desc-full').classList.remove('hidden');
}
function collapseDesc(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.querySelector('.desc-short').classList.remove('hidden');
  el.querySelector('.desc-full').classList.add('hidden');
}

/* ---- Render sub_items recursively ---- */
function renderSubItems(items, caps, paramCache, status, depth, forceDisabled = false) {
  if (!items) return '';
  let html = '';
  items.forEach(item => {
    html += renderSettingItem(item, caps, paramCache, status, depth, forceDisabled);
    const parentVal = paramCache[item.key];
    const parentOn = parentVal === '1' || String(parentVal).toLowerCase() === 'true';
    if (item.sub_items && parentOn) {
      html += renderSubItems(item.sub_items, caps, paramCache, status, depth + 1, forceDisabled);
    }
  });
  return html;
}

/* ---- Poll offroad state while settings page is active ---- */
function startSettingsStatusPoll() {
  if (settingsStatusInterval) return;
  settingsStatusInterval = setInterval(async () => {
    try {
      const s = await api('/api/status', { silent: true });
      if (s.is_offroad !== settingsStatus.is_offroad || s.is_metric !== settingsStatus.is_metric || s.engaged !== settingsStatus.engaged) {
        settingsStatus = s;
        maybeReEval();
      }
    } catch {}
  }, 3000);
}
function stopSettingsStatusPoll() {
  clearInterval(settingsStatusInterval);
  settingsStatusInterval = null;
}

/* ---- Main settings loader ---- */
async function loadSettings() {
  startSettingsStatusPoll();
  const container = document.getElementById('settings-panels');
  try {
    const [schema, caps, status_] = await Promise.all([
      api('/api/settings/schema'),
      api('/api/capabilities'),
      api('/api/status'),
    ]);
    settingsSchema = schema;
    settingsCapabilities = caps;
    settingsStatus = status_;

    /* Collect all param keys from items + rules */
    const neededKeys = new Set();
    function walkItems(items) {
      if (!items) return;
      items.forEach(item => {
        if (item.key) neededKeys.add(item.key);
        if (item.title_param_suffix && item.title_param_suffix.param) neededKeys.add(item.title_param_suffix.param);
        [item.visibility, item.enablement].forEach(rules => {
          if (rules) walkRules(rules);
        });
        (item.options || []).forEach(o => {
          if (o.enablement) walkRules(o.enablement);
        });
        if (item.sub_items) walkItems(item.sub_items);
      });
    }
    function walkRules(rules) {
      rules.forEach(r => {
        if (r.type === 'param' || r.type === 'param_compare') neededKeys.add(r.key);
        if (r.condition) walkRules([r.condition]);
        if (r.conditions) walkRules(r.conditions);
      });
    }
    (schema.panels || []).forEach(p => {
      (p.sections || []).forEach(s => {
        walkItems(s.items);
        (s.sub_panels || []).forEach(sp => walkItems(sp.items));
      });
      walkItems(p.items);
      (p.sub_panels || []).forEach(sp => walkItems(sp.items));
    });
    Object.values(schema.vehicle_settings || {}).forEach(v => walkItems(v.items || v));

    /* Batch-fetch all needed param values */
    const paramPromises = [...neededKeys].map(async k => {
      try {
        const r = await api(`/api/params/${k}`, { silent: true });
        settingsParamCache[k] = r.value;
      } catch { settingsParamCache[k] = null; }
    });
    await Promise.all(paramPromises);

    try { settingsFavorites = await api('/api/settings/favorites'); } catch { settingsFavorites = []; }

    renderSettingsUI();
  } catch (e) {
    console.error('loadSettings error:', e);
    container.innerHTML = '<p>Could not load settings schema.</p><pre style="color:var(--red);font-size:0.8rem;margin-top:0.5rem">' + e.message + '</pre>';
  }
}

function renderSettingsUI() {
  const schema = settingsSchema;
  const caps = settingsCapabilities;
  const pc = settingsParamCache;
  const st = settingsStatus;
  const container = document.getElementById('settings-panels');

  /* Offroad status banner */
  let offroadBanner = document.getElementById('offroad-status-banner');
  if (!offroadBanner) {
    offroadBanner = document.createElement('div');
    offroadBanner.id = 'offroad-status-banner';
    container.parentElement.insertBefore(offroadBanner, container);
  }
  if (st.is_offroad) {
    offroadBanner.className = 'offroad-banner offroad-banner-on';
    offroadBanner.innerHTML = '&#9989; Offroad &mdash; offroad settings unlocked (some may still be vehicle-specific)';
  } else {
    offroadBanner.className = 'offroad-banner offroad-banner-off';
    offroadBanner.innerHTML = '&#128664; Onroad &mdash; <span class="badge-offroad">Offroad</span> settings are locked until parked';
  }

  function subPanelVisible(sub) {
    if (!sub.trigger_key) return true;
    const val = pc[sub.trigger_key];
    if (sub.trigger_condition === undefined) return val === '1' || val === true;
    if (sub.trigger_condition && typeof sub.trigger_condition === 'object')
      return evaluateRule(sub.trigger_condition, caps, pc, st);
    return String(val) === String(sub.trigger_condition);
  }

  const q = settingsSearchQuery;
  function itemMatches(item) {
    if (!q) return true;
    const title = (item.title || '').toLowerCase();
    const desc = (item.description || '').replace(/<[^>]+>/g, ' ').toLowerCase();
    const key = (item.key || '').toLowerCase();
    return title.includes(q) || desc.includes(q) || key.includes(q);
  }

  let html = '';

  /* Favorites panel */
  if (settingsFavorites.length) {
    const favSet = new Set(settingsFavorites);
    const favItems = [];
    function collectFav(items) {
      if (!items) return;
      items.forEach(item => {
        if (item.key && favSet.has(item.key) && evaluateRules(item.visibility, caps, pc, st)) {
          favItems.push(item);
        }
        if (item.sub_items) collectFav(item.sub_items);
      });
    }
    (schema.panels || []).forEach(p => {
      (p.sections || []).forEach(s => {
        collectFav(s.items);
        (s.sub_panels || []).forEach(sp => collectFav(sp.items));
      });
      collectFav(p.items);
      (p.sub_panels || []).forEach(sp => collectFav(sp.items));
    });
    Object.values(schema.vehicle_settings || {}).forEach(v => collectFav(v.items || v));
    if (favItems.length) {
      let favHtml = `<div class="panel"><div class="panel-header">&#11088; Favorites</div><div class="panel-section">`;
      favHtml += renderSubItems(favItems, caps, pc, st, 0);
      favHtml += `</div></div>`;
      html += favHtml;
    }
  }

  let totalItems = 0;
  let visibleItems = 0;
  for (const panel of schema.panels || []) {
    if (!evaluateRules(panel.visibility, caps, pc, st)) continue;
    const panelLabel = (panel.label || '').toLowerCase();
    const panelMatch = !q || panelLabel.includes(q);

    let panelHtml = '';
    for (const section of panel.sections || []) {
      if (!evaluateRules(section.visibility, caps, pc, st)) continue;
      const sectionEnabled = evaluateRules(section.enablement, caps, pc, st);
      const sectionTitle = (section.title || '').toLowerCase();
      const sectionDesc = (section.description || '').toLowerCase();
      const sectionMatch = panelMatch || !q || sectionTitle.includes(q) || sectionDesc.includes(q);

      const sectionItems = (section.items || []).filter(itemMatches);
      const matchingSubPanels = (section.sub_panels || []).filter(sub => {
        if (!subPanelVisible(sub)) return false;
        if (sectionMatch || panelMatch) return true;
        return (sub.items || []).some(itemMatches);
      });

      if (!sectionItems.length && !matchingSubPanels.length) continue;

      const sectionCount = (section.items || []).length;
      let sectionHtml = '';
      if (section.title) sectionHtml += `<div class="section-title">${section.title}</div>`;
      if (section.description) sectionHtml += `<div class="section-desc">${section.description}</div>`;
      sectionHtml += renderSubItems(sectionItems, caps, pc, st, 0, !sectionEnabled);
      totalItems += sectionCount;
      visibleItems += sectionItems.length;
      for (const sub of matchingSubPanels) {
        if (sub.title || sub.label) sectionHtml += `<div class="section-title">${sub.title || sub.label}</div>`;
        const subItems = (sub.items || []).filter(itemMatches);
        totalItems += (sub.items || []).length;
        visibleItems += subItems.length;
        sectionHtml += renderSubItems(subItems, caps, pc, st, 0, !sectionEnabled);
      }
      panelHtml += `<div class="panel-section">${sectionHtml}</div>`;
    }
    if (!panelHtml) continue;
    html += `<div class="panel"><div class="panel-header">${panel.label}</div>${panelHtml}</div>`;
  }

  /* vehicle_settings: filter by current car brand if capability data available */
  const carBrand = (caps.brand || '').toLowerCase();
  for (const [brand, vs] of Object.entries(schema.vehicle_settings || {})) {
    if (carBrand && brand.toLowerCase() !== carBrand) continue;
    const items = (vs.items || vs).filter(itemMatches);
    const vsCount = (vs.items || vs).length;
    totalItems += vsCount;
    visibleItems += items.length;
    if (!items || !items.length) continue;
    html += `<div class="panel"><div class="panel-header">Vehicle Settings: ${brand}</div>`;
    html += `<div class="panel-section">`;
    html += renderSubItems(items, caps, pc, st, 0);
    html += `</div></div>`;
  }

  container.innerHTML = html;

  const countEl = document.getElementById('settings-search-count');
  if (countEl) countEl.textContent = q ? `${visibleItems} / ${totalItems}` : '';

  /* Wire up toggle events — queue change, don't apply immediately */
  container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', (e) => {
      if (e.target.dataset.attestation === '1') {
        e.target.checked = !e.target.checked; // revert
        toast('This setting can only be changed on the device itself', 'error');
        return;
      }
      const key = e.target.dataset.param;
      const val = e.target.checked ? '1' : '0';
      const labelEl = e.target.closest('.section-item')?.querySelector('.item-title');
      const label = labelEl ? labelEl.textContent.trim() : key;
      const needsCycle = e.target.closest('.section-item')?.querySelector('.badge-restart') !== null;
      queueChange(key, val, label, needsCycle);
    });
  });

  /* Wire up all <select> controls — queue change */
  container.querySelectorAll('select.setting-select').forEach(sel => {
    sel.addEventListener('change', (e) => {
      if (e.target.dataset.attestation === '1') {
        toast('This setting can only be changed on the device itself', 'error');
        return;
      }
      const key = e.target.dataset.param;
      const val = e.target.value;
      const labelEl = e.target.closest('.section-item')?.querySelector('.item-title');
      const label = labelEl ? labelEl.textContent.trim() : key;
      const needsCycle = e.target.closest('.section-item')?.querySelector('.badge-restart') !== null;
      queueChange(key, val, label, needsCycle);
    });
  });

  /* Wire up numeric stepper buttons */
  container.querySelectorAll('button.num-edit-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const key = e.target.dataset.param;
      openNumModal(
        key,
        settingsParamCache[key],
        e.target.dataset.min,
        e.target.dataset.max,
        e.target.dataset.step,
        e.target.dataset.label,
        e.target.dataset.needsCycle === '1',
      );
    });
  });

  /* Wire up calibrate buttons */
  container.querySelectorAll('button.calibrate-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const key = e.target.dataset.param;
      openCalibrateModal(
        key,
        settingsParamCache[key],
        e.target.dataset.min,
        e.target.dataset.max,
        e.target.dataset.step,
        e.target.dataset.label,
        e.target.dataset.needsCycle === '1',
      );
    });
  });

  /* Wire up button events — apply immediately (one-shot action, not a setting) */
  container.querySelectorAll('button.action-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const key = e.target.dataset.param;
      try {
        await api(`/api/params/${key}`, { method: 'POST', body: JSON.stringify({ value: '1' }) });
        toast(`Executed ${key}`, 'success');
      } catch {}
    });
  });
}

function maybeReEval() {
  if (reEvalPending) return;
  reEvalPending = true;
  requestAnimationFrame(() => {
    reEvalPending = false;
    renderSettingsUI();
  });
}

function onSettingsSearchInput() {
  settingsSearchQuery = (document.getElementById('settings-search')?.value || '').toLowerCase().trim();
  toggleSearchClear('settings');
  renderSettingsUI();
}
function clearSettingsSearch() {
  document.getElementById('settings-search').value = '';
  settingsSearchQuery = '';
  toggleSearchClear('settings');
  renderSettingsUI();
}
function clearModelSearch() {
  document.getElementById('model-search').value = '';
  document.getElementById('model-search-clear').classList.remove('visible');
  filterModels();
}
function toggleSearchClear(prefix) {
  const inp = document.getElementById(prefix + '-search');
  const btn = document.getElementById(prefix + '-search-clear');
  if (inp && btn) btn.classList.toggle('visible', inp.value.length > 0);
}

/* ============ MODELS ============ */
let modelsData = null;
let modelsProgressInterval = null;

function stopModelsProgressPoll() {
  if (modelsProgressInterval) { clearInterval(modelsProgressInterval); modelsProgressInterval = null; }
}

async function loadModels() {
  try {
    const [active, bundles, favorites] = await Promise.all([
      api('/api/models/active'),
      api('/api/models'),
      api('/api/models/favorites'),
    ]);
    modelsData = { active, bundles, favorites };

    document.getElementById('active-model-name').textContent = active.displayName || active.internalName || '—';
    document.getElementById('active-model-runner').textContent = active.runner !== undefined ? fmtRunner(active.runner) : 'Stock';
    document.getElementById('active-model-gen').textContent = active.generation !== undefined ? active.generation : '—';
    document.getElementById('active-model-env').textContent = active.environment || '—';

    renderBundleList(bundles, active, favorites);
    checkCacheSize();

    /* Start progress polling */
    checkDownloadProgress();
    if (modelsProgressInterval) clearInterval(modelsProgressInterval);
    modelsProgressInterval = setInterval(checkDownloadProgress, 2000);
  } catch (e) {
    document.getElementById('model-list').innerHTML = '<p style="color:var(--text-dim)">Failed to load models.</p>';
  }
}

function renderBundleList(bundles, active, favorites) {
  const container = document.getElementById('model-list');
  if (!bundles || !bundles.length) {
    container.innerHTML = '<p style="color:var(--text-dim)">No models available. Try refreshing.</p>';
    return;
  }

  const activeRef = active.ref;
  const favSet = new Set(favorites || []);

  /* Group by folder from overrides */
  const folders = {};
  bundles.forEach(b => {
    const folder = b.overrides ? (b.overrides.find(o => o.key === 'folder') || {}).value || '' : '';
    if (!folders[folder]) folders[folder] = [];
    folders[folder].push(b);
  });

  /* Sort: favorites first within each folder */
  let html = '';
  const folderOrder = Object.keys(folders).sort((a, b) => {
    if (!a) return 1; if (!b) return -1;
    return a.localeCompare(b);
  });

  folderOrder.forEach(folder => {
    const items = folders[folder];
    html += `<div class="model-folder">`;
    if (folder) html += `<div class="folder-title">${folder}</div>`;
    items.forEach(b => {
      const isActive = b.ref === activeRef || b.internalName === active.internalName;
      const isFav = favSet.has(b.ref);
      const isCached = !!b.isCached;
      const safeDisplayName = (b.displayName || b.internalName).replace(/'/g,"\\'");
      const safeInternalName = (b.internalName || '').replace(/'/g,"\\'");
      const actionLabel = isCached ? 'Select' : 'Download';
      const actionCls   = isCached ? 'btn-primary' : 'btn-download';
      const deleteBtn   = isCached && !isActive
        ? `<button class="btn btn-sm btn-danger model-delete-btn" onclick="deleteModel('${safeInternalName}', '${safeDisplayName}')" title="Delete from disk">🗑</button>`
        : '';
      html += `<div class="model-item">
        <div class="model-item-info">
          <div class="model-item-name">${b.displayName || b.internalName}</div>
          <div class="model-item-meta">Gen ${b.generation || '?'} &middot; ${b.environment || '—'} &middot; ${fmtRunner(b.runner)}${b.is20hz ? ' &middot; 20Hz' : ''}${isCached ? ' &middot; <span class="meta-cached">cached</span>' : ''}</div>
        </div>
        <div class="model-item-actions">
          <button class="fav-btn ${isFav ? 'active' : ''}" onclick="toggleFav('${b.ref}', this)" title="Favorite">${isFav ? '★' : '☆'}</button>
          ${isActive ? '<span class="model-badge active-model">Active</span>' : `<button class="btn btn-sm ${actionCls}" onclick="selectModel(${b.index}, '${safeDisplayName}', ${isCached})">${actionLabel}</button>`}
          ${deleteBtn}
        </div>
      </div>`;
    });
    html += `</div>`;
  });

  container.innerHTML = html;
}

const filterModels = debounce(() => {
  if (!modelsData) return;
  toggleSearchClear('model');
  const query = document.getElementById('model-search').value.toLowerCase();
  const bundles = (modelsData.bundles || []).filter(b =>
    (b.displayName || '').toLowerCase().includes(query) ||
    (b.internalName || '').toLowerCase().includes(query)
  );
  renderBundleList(bundles, modelsData.active, modelsData.favorites);
}, 200);

async function refreshModelList() {
  await api('/api/models/refresh', { method: 'POST' });
  toast('Refreshing model list…', 'info');
  let attempts = 0;
  const poll = setInterval(async () => {
    attempts++;
    try {
      const bundles = await api('/api/models');
      if (bundles && bundles.length) {
        clearInterval(poll);
        await loadModels();
        toast('Model list updated', 'success');
      }
    } catch {}
    if (attempts >= 15) clearInterval(poll);
  }, 1000);
}

async function selectModel(index, name, isCached) {
  const verb = isCached ? 'Select' : 'Download';
  const detail = isCached
    ? 'Already cached — will switch to this model immediately.'
    : 'Not on device yet — a download will start.';
  showModal(`${verb} Model`,
    `<p><b>${name}</b></p><p>${detail}</p>`,
    [
      { label: 'Cancel', cls: '' },
      { label: verb, action: `doSelectModel(${index}, '${name.replace(/'/g,"\\'")}', ${!!isCached})`, cls: 'btn-primary' },
    ]
  );
}

async function doSelectModel(index, name, isCached) {
  try {
    await api('/api/models/select', { method: 'POST', body: JSON.stringify({ index }) });
    if (isCached) {
      toast(`Switched to ${name}`, 'success');
      loadModels();
    } else {
      toast(`Download started: ${name}`, 'info');
      /* Scroll to top so progress bar is visible */
      document.getElementById('page-models').scrollIntoView({ behavior: 'smooth', block: 'start' });
      window.scrollTo({ top: 0, behavior: 'smooth' });
      /* Start polling progress */
      if (modelsProgressInterval) clearInterval(modelsProgressInterval);
      modelsProgressInterval = setInterval(checkDownloadProgress, 2000);
      checkDownloadProgress();
    }
  } catch (e) {
    toast(`Failed to ${isCached ? 'select' : 'start download for'} ${name}`, 'error');
  }
}

async function deleteModel(internalName, displayName) {
  showModal('Delete Model', `<p>Delete <b>${escHtml(displayName)}</b> from disk?<br>You can re-download it later.</p>`, [
    { label: 'Cancel', action: '', cls: '' },
    { label: 'Delete', action: `doDeleteModel('${internalName.replace(/'/g,"\\'")}','${displayName.replace(/'/g,"\\'")}')`, cls: 'btn-danger' },
  ]);
}

async function doDeleteModel(internalName, displayName) {
  try {
    const res = await api(`/api/models/${encodeURIComponent(internalName)}`, { method: 'DELETE' });
    toast(`Deleted ${displayName} (${res.deleted?.length || 0} files)`, 'success');
    loadModels();
  } catch (e) {
    toast(`Delete failed: ${e.message || e}`, 'error');
  }
}

async function selectDefaultModel() {
  showModal('Use Default Model', `<p>Switch to the default built-in model?</p>`, [
    { label: 'Cancel', action: '', cls: '' },
    { label: 'Use Default', action: `api('/api/models/select/default',{method:'POST'})&&toast('Switched to default model','success')&&loadModels()`, cls: 'btn-primary' },
  ]);
}

async function cancelDownload() {
  await api('/api/models/cancel', { method: 'POST' });
  toast('Download cancelled', 'info');
  document.getElementById('model-dl-progress').classList.add('hidden');
}

async function clearModelCache() {
  showModal('Clear Model Cache', `<p>Remove all downloaded models except the active one?</p>`, [
    { label: 'Cancel', action: '', cls: '' },
    { label: 'Clear', action: `api('/api/models/cache',{method:'DELETE'})&&toast('Cache clearing triggered','success')`, cls: 'btn-danger' },
  ]);
}

async function toggleFav(ref, btn) {
  if (!ref) return;
  const current = await api('/api/models/favorites');
  let refs = current || [];
  if (refs.includes(ref)) {
    refs = refs.filter(r => r !== ref);
  } else {
    refs.push(ref);
  }
  await api('/api/models/favorites', { method: 'POST', body: JSON.stringify({ refs }) });
  btn.classList.toggle('active');
  btn.textContent = btn.classList.contains('active') ? '★' : '☆';
  if (modelsData) modelsData.favorites = refs;
}

async function toggleSettingsFav(key, btn) {
  if (!key) return;
  let refs = [...settingsFavorites];
  if (refs.includes(key)) { refs = refs.filter(r => r !== key); }
  else { refs.push(key); }
  await api('/api/settings/favorites', { method: 'POST', body: JSON.stringify({ refs }) });
  settingsFavorites = refs;
  renderSettingsUI();
}

async function checkCacheSize() {
  try {
    const [active, bundles] = await Promise.all([
      api('/api/models/active'),
      api('/api/models'),
    ]);
    /* Count models in bundle to estimate - real size would need disk check */
    document.getElementById('model-cache-size').textContent = `${bundles.length} model${bundles.length !== 1 ? 's' : ''} available`;
  } catch {}
}

async function checkDownloadProgress() {
  try {
    const progress = await api('/api/models/progress');
    if (!progress || progress.error) {
      document.getElementById('model-dl-progress').classList.add('hidden');
      return;
    }
    const sel = progress.selectedBundle;
    if (!sel) {
      document.getElementById('model-dl-progress').classList.add('hidden');
      return;
    }
    document.getElementById('model-dl-progress').classList.remove('hidden');
    document.getElementById('dl-bundle-name').textContent = sel.displayName || sel.internalName || '';

    const allModels = sel.models || [];
    const MODEL_TYPES = ['Supercombo','Navigation','Vision','Policy','Off-Policy','On-Policy'];
    let html = '';
    let allDone = true;
    allModels.forEach(m => {
      const dp = m.artifact && m.artifact.downloadProgress;
      const mp = m.metadata && m.metadata.downloadProgress;
      if (!dp) return;
      /* Combine artifact + metadata into one bar; metadata is a small JSON so weight 90/10 */
      const artifactPct = dp.progress || 0;
      const metaPct     = (mp && mp.progress) || 0;
      const pct         = mp ? artifactPct * 0.9 + metaPct * 0.1 : artifactPct;
      const status      = dp.status; // drive status from artifact (the large file)
      const metaStatus  = mp ? mp.status : status;
      const combinedStatus = (status >= 2 && metaStatus >= 2) ? Math.max(status, metaStatus) : Math.min(status, metaStatus);
      const eta = dp.eta || 0;
      const statusText = fmtDownloadStatus(combinedStatus);
      const isFailed = combinedStatus === 4;
      const isDone = combinedStatus >= 2;
      const isCached = combinedStatus === 3;
      if (!isDone) allDone = false;
      let fillCls = '';
      if (isDone) fillCls = isCached ? ' cached' : (isFailed ? ' failed' : ' done');
      const typeLabel = m.type !== undefined ? (MODEL_TYPES[m.type] || 'Model') : 'Model';
      html += `<div class="progress-item">
        <div class="progress-header">
          <span class="progress-type">${typeLabel}</span>
          <span class="progress-status">${statusText}${!isDone && !isFailed ? ' ' + pct.toFixed(0) + '%' + (eta ? ' ETA ' + eta + 's' : '') : ''}</span>
        </div>
        <div class="progress-bar"><div class="progress-fill${fillCls}" style="width:${Math.max(pct,2)}%"></div></div>
      </div>`;
    });
    document.getElementById('dl-progress-items').innerHTML = html;

    if (allDone) {
      /* Download complete - reload models after short delay */
      setTimeout(() => { loadModels(); }, 1000);
    }
  } catch {}
}

/* ============ VEHICLE ============ */
let vehicleData = null;
let vehiclePlatforms = null;
let fingerprintDiag = null;

async function loadVehicle() {
  try {
    const [vehicle, platforms] = await Promise.all([
      api('/api/vehicle'),
      api('/api/vehicle/platforms'),
    ]);
    vehicleData = vehicle;
    vehiclePlatforms = platforms;
    renderVehicleUI();
  } catch (e) {
    document.getElementById('vehicle-name').textContent = 'Error loading vehicle';
  }
  loadFingerprintDiagnostics();
  loadIgnitionDiagnostics();
}

async function loadIgnitionDiagnostics() {
  try {
    ignitionDiag = await api('/api/vehicle/ignition_diagnostics');
    renderIgnitionDiagnostics();
  } catch (e) {
    console.error('Failed to load ignition diagnostics:', e);
  }
}

function saveExpandedSteps(prefix) {
  return [...document.querySelectorAll(`[id^="${prefix}-step-"].fp-expanded`)].map(
    el => el.id.replace(`${prefix}-step-`, '')
  );
}

function restoreExpandedSteps(prefix, ids) {
  ids.forEach(id => {
    const el = document.getElementById(`${prefix}-step-${id}`);
    if (el) el.classList.add('fp-expanded');
  });
}

function renderIgnitionDiagnostics() {
  const container = document.getElementById('ignition-workflow');
  if (!container || !ignitionDiag) return;

  const { decision_tree, result, panda_info, startup_conditions, history } = ignitionDiag;

  let treeHtml = '<div class="fp-tree">';
  treeHtml += '<div class="fp-tree-title">DECISION TREE</div>';
  treeHtml += '<div class="fp-tree-branches">';
  decision_tree.forEach((branch, i) => {
    const cls = branch.status === 'winner' ? 'fp-winner' : branch.status === 'overridden' ? 'fp-overridden' : branch.status === 'failed' ? 'fp-failed' : 'fp-skipped';
    const icon = branch.status === 'winner' ? '✓' : branch.status === 'overridden' ? '→' : branch.status === 'failed' ? '✗' : '○';
    const arrow = i < decision_tree.length - 1 ? '<div class="fp-tree-arrow">↓</div>' : '';

    let detailsHtml = '';
    if (branch.details && Object.keys(branch.details).length > 0) {
      detailsHtml += '<div class="fp-step-details">';
      for (const [key, value] of Object.entries(branch.details)) {
        const displayValue = value === null ? 'null' : value === undefined ? 'N/A' : Array.isArray(value) ? value.join(', ') : String(value);
        detailsHtml += `<div class="fp-detail-row"><span class="fp-detail-key">${key}:</span><span class="fp-detail-value">${displayValue}</span></div>`;
      }
      detailsHtml += '</div>';
    }

    let winnerNotice = branch.status === 'winner' ? '<div class="fp-winner-notice">✓ THIS STEP DETERMINED THE FINAL STATE</div>' : '';
    let overrideNotice = branch.status === 'overridden' ? '<div class="fp-override-notice">OVERRIDDEN — Condition not met, fallback to next step</div>' : '';

    treeHtml += `
      <div class="fp-tree-branch ${cls}" onclick="toggleIgnitionStep(${branch.num})">
        <div class="fp-tree-branch-header">
          <span class="fp-tree-num">${branch.num}</span>
          <span class="fp-tree-icon">${icon}</span>
          <span class="fp-tree-condition">${branch.condition}</span>
          <span class="fp-step-status">${branch.status.toUpperCase()}</span>
        </div>
        <div class="fp-tree-result">${branch.result}</div>
        <div class="fp-step-content" id="ignition-step-${branch.num}">
          ${winnerNotice}
          ${overrideNotice}
          ${detailsHtml}
        </div>
      </div>
      ${arrow}
    `;
  });
  treeHtml += '</div></div>';
  document.getElementById('ignition-tree').innerHTML = treeHtml;

  let pandaInfoHtml = '';
  if (panda_info && panda_info.panda_states && panda_info.panda_states.length > 0) {
    const ps = panda_info.panda_states[0];
    pandaInfoHtml = `
      <div class="ignition-panda-info">
        <div class="panda-info-row"><span class="panda-info-label">Pandas Connected:</span><span class="panda-info-value">${panda_info.count}</span></div>
        <div class="panda-info-row"><span class="panda-info-label">Voltage:</span><span class="panda-info-value">${ps.voltage ? ps.voltage.toFixed(1) + 'V' : 'N/A'}</span></div>
        <div class="panda-info-row"><span class="panda-info-label">Temperature:</span><span class="panda-info-value">${ps.temperature ? ps.temperature + '°C' : 'N/A'}</span></div>
        <div class="panda-info-row"><span class="panda-info-label">Serial:</span><span class="panda-info-value">${ps.serial || 'N/A'}</span></div>
      </div>
    `;
  }

  let startupConditionsHtml = '';
  if (startup_conditions) {
    const conditions = [
      { key: 'Thermal', val: startup_conditions.thermal, icon: startup_conditions.thermal.blocking ? '✗' : '✓' },
      { key: 'Space', val: startup_conditions.space, icon: startup_conditions.space.blocking ? '✗' : '✓' },
      { key: 'Terms', val: startup_conditions.terms, icon: startup_conditions.terms.blocking ? '✗' : '✓' },
      { key: 'Offroad', val: startup_conditions.offroad, icon: startup_conditions.offroad.blocking ? '✗' : '✓' },
      { key: 'Panda', val: startup_conditions.panda, icon: startup_conditions.panda.blocking ? '✗' : '✓' },
    ];
    startupConditionsHtml = '<div class="ignition-startup-conditions">';
    conditions.forEach(c => {
      const val = c.val;
      const st = c.icon === '✓' ? 'ok' : 'blocking';
      let extra = '';
      if (val.status) extra = ` (${val.status})`;
      else if (val.free_pct !== undefined && val.free_pct !== null) extra = ` (${val.free_pct}% free)`;
      startupConditionsHtml += `<div class="startup-condition ${st}">${c.icon} ${c.key}: ${val.blocking ? 'BLOCKING' : 'OK'}${extra}</div>`;
    });
    startupConditionsHtml += '</div>';
  }

  let historyHtml = '';
  if (history && history.length > 0) {
    historyHtml = '<div class="ignition-history">';
    history.forEach(h => {
      historyHtml += `<div class="history-item">${h.msg.substring(0, 80)}...</div>`;
    });
    historyHtml += '</div>';
  }

  container.innerHTML = '<div class="ignition-extras">' + pandaInfoHtml + startupConditionsHtml + historyHtml + '</div>';
}

function toggleIgnitionStep(stepId) {
  const el = document.getElementById(`ignition-step-${stepId}`);
  if (el) el.closest('.fp-tree-branch')?.classList.toggle('fp-expanded');
}

let ignitionDiag = null;

async function loadFingerprintDiagnostics() {
  try {
    fingerprintDiag = await api('/api/vehicle/fingerprint_diagnostics');
    renderFingerprintDiagnostics();
  } catch (e) {
    console.error('Failed to load fingerprint diagnostics:', e);
  }
}

function renderFingerprintDiagnostics() {
  const container = document.getElementById('fingerprint-workflow');
  if (!container || !fingerprintDiag) return;

  const { decision_tree, steps, result, cached_historical } = fingerprintDiag;

  let treeHtml = '<div class="fp-tree">';
  treeHtml += '<div class="fp-tree-title">DECISION TREE</div>';
  treeHtml += '<div class="fp-tree-branches">';
  decision_tree.forEach((branch, i) => {
    const cls = branch.status === 'winner' ? 'fp-winner' : branch.status === 'overridden' ? 'fp-overridden' : branch.status === 'failed' ? 'fp-failed' : 'fp-skipped';
    const icon = branch.status === 'winner' ? '\u2713' : branch.status === 'overridden' ? '\u2192' : branch.status === 'failed' ? '\u2717' : '\u25CB';
    const arrow = i < decision_tree.length - 1 ? '<div class="fp-tree-arrow">\u2193</div>' : '';

    const step = steps.find(s => s.id === branch.num);
    const stepTitle = step ? step.title : '';
    const stepAction = step ? step.action : '';

    let detailsHtml = '';
    if (branch.details && Object.keys(branch.details).length > 0) {
      detailsHtml += '<div class="fp-step-details">';
      for (const [key, value] of Object.entries(branch.details)) {
        const displayValue = value === null ? 'null' : value === undefined ? 'N/A' : Array.isArray(value) ? value.join(', ') : String(value);
        detailsHtml += '<div class="fp-detail-row"><span class="fp-detail-key">' + key + ':</span><span class="fp-detail-value">' + displayValue + '</span></div>';
      }
      detailsHtml += '</div>';
    }

    let failureReasonsHtml = '';
    if (step && step.failure_reasons && step.failure_reasons.length > 0) {
      failureReasonsHtml += '<div class="fp-failure-reasons">';
      failureReasonsHtml += '<div class="fp-failure-header">Why it would FAIL:</div>';
      step.failure_reasons.forEach(reason => {
        failureReasonsHtml += '<div class="fp-failure-item">\u2514\u2500 ' + reason + '</div>';
      });
      failureReasonsHtml += '</div>';
    }

    let winnerNotice = branch.status === 'winner' ? '<div class="fp-winner-notice">\u2713 THIS STEP DETERMINED THE FINAL FINGERPRINT</div>' : '';
    let overrideNotice = branch.status === 'overridden' ? '<div class="fp-override-notice">OVERRIDDEN \u2014 Condition not met, fallback to next step</div>' : '';

    treeHtml += [
      '<div class="fp-tree-branch ' + cls + '" onclick="toggleFingerprintStep(' + branch.num + ')">',
      '  <div class="fp-tree-branch-header">',
      '    <span class="fp-tree-num">' + branch.num + '</span>',
      '    <span class="fp-tree-icon">' + icon + '</span>',
      '    <span class="fp-tree-condition">' + branch.condition + '</span>',
      '    <span class="fp-step-status">' + branch.status.toUpperCase() + '</span>',
      '  </div>',
      '  <div class="fp-tree-result">' + branch.result + '</div>',
      '  <div class="fp-step-content" id="fp-step-' + branch.num + '">',
      (stepTitle ? '    <div class="fp-decision-logic">Step ' + branch.num + ': ' + stepTitle.toUpperCase() + '</div>' : ''),
      (stepAction ? '    <div class="fp-action">Action: ' + stepAction + '</div>' : ''),
      '    ' + winnerNotice,
      '    ' + overrideNotice,
      '    ' + detailsHtml,
      '    ' + failureReasonsHtml,
      '  </div>',
      '</div>',
      arrow,
    ].filter(Boolean).join('\n');
  });
  treeHtml += '</div></div>';
  document.getElementById('fp-tree').innerHTML = treeHtml;

  let cachedHistoricalHtml = '';
  if (cached_historical) {
    cachedHistoricalHtml = [
      '<div class="fp-cached-historical">',
      '  <div class="fp-cached-header">\u26A0\uFE0F CACHED FINGERPRINT FROM PREVIOUS BOOT</div>',
      '  <div class="fp-cached-note">' + cached_historical.note + '</div>',
      '  <div class="fp-cached-details">',
      '    <div class="fp-cached-row"><span>Original source:</span><span>' + cached_historical.source + ' (' + cached_historical.source_step + ')</span></div>',
      '    <div class="fp-cached-row"><span>Fingerprint:</span><span>' + cached_historical.fingerprint + '</span></div>',
      '    <div class="fp-cached-row"><span>VIN:</span><span>' + (cached_historical.vin || 'N/A') + '</span></div>',
      '    <div class="fp-cached-row"><span>ECUs:</span><span>' + cached_historical.ecus + '</span></div>',
      '    <div class="fp-cached-row"><span>Fuzzy match:</span><span>' + (cached_historical.fuzzy ? 'Yes' : 'No') + '</span></div>',
      '  </div>',
      '</div>'
    ].join('\n');
  }

  let resultHtml = '';
  if (result) {
    const isSuccess = result.status !== 'mock';
    const resultIcon = isSuccess ? '\u2713' : '\u2717';
    const resultClass = isSuccess ? 'fp-success' : 'fp-failed';
    resultHtml = [
      '<div class="fp-result ' + resultClass + '">',
      '  <div class="fp-result-header">',
      '    <span class="fp-result-icon">' + resultIcon + '</span>',
      '    <span class="fp-result-title">' + (result.status === 'mock' ? 'MOCK FALLBACK' : 'FINGERPRINTED') + '</span>',
      (result.winner_branch ? '    <span class="fp-winner-badge">Step ' + result.winner_branch + ' won</span>' : ''),
      '  </div>',
      '  <div class="fp-result-summary">',
      '    ' + (result.fingerprint || 'No fingerprint') + (result.source ? ' \u2022 Source: ' + result.source : '') + (result.is_fuzzy_match !== null ? ' \u2022 Fuzzy: ' + (result.is_fuzzy_match ? 'Yes' : 'No') : ''),
      '  </div>',
      (result.vin ? '  <div class="fp-result-vin">VIN: ' + result.vin + '</div>' : ''),
      (fingerprintDiag.platform_info && fingerprintDiag.platform_info.dbc_names ? '  <div class="fp-result-dbc">DBC: ' + fingerprintDiag.platform_info.dbc_names.join(', ') + '</div>' : ''),
      '</div>'
    ].filter(Boolean).join('\n');
  }

  container.innerHTML = cachedHistoricalHtml + resultHtml;
}
function toggleFingerprintStep(stepId) {
  const el = document.getElementById(`fp-step-${stepId}`);
  if (el) el.closest('.fp-tree-branch')?.classList.toggle('fp-expanded');
}

function renderVehicleUI() {
  if (!vehicleData) return;
  const nameEl = document.getElementById('vehicle-name');
  const badgeEl = document.getElementById('vehicle-status-badge');
  const detailsEl = document.getElementById('vehicle-status-details');
  const actionsEl = document.getElementById('vehicle-actions');

  const { platform_bundle, fingerprint, status } = vehicleData;

  let displayName = 'Unrecognized Vehicle';
  let badgeText = '';
  let badgeClass = 'badge-unrecognized';

  if (status === 'manual' && platform_bundle) {
    displayName = platform_bundle.name || 'Manual Selection';
    badgeText = 'Manual';
    badgeClass = 'badge-manual';
  } else if (status === 'auto' && fingerprint) {
    displayName = fingerprint;
    badgeText = 'Auto-detected';
    badgeClass = 'badge-auto';
  }

  nameEl.textContent = displayName;
  badgeEl.textContent = badgeText;
  badgeEl.className = 'vehicle-status-badge ' + badgeClass;

  let detailsHtml = '';
  if (status === 'auto' && fingerprint) {
    detailsHtml += `<div class="detail-row"><span class="label">Fingerprint:</span><span class="value">${fingerprint}</span></div>`;
  }
  if (platform_bundle) {
    detailsHtml += `<div class="detail-row"><span class="label">Platform:</span><span class="value">${platform_bundle.platform || '—'}</span></div>`;
    detailsHtml += `<div class="detail-row"><span class="label">Make:</span><span class="value">${platform_bundle.make || '—'}</span></div>`;
    detailsHtml += `<div class="detail-row"><span class="label">Brand:</span><span class="value">${platform_bundle.brand || '—'}</span></div>`;
  }
  detailsEl.innerHTML = detailsHtml;

  let actionsHtml = '';
  if (status === 'manual' || status === 'auto') {
    actionsHtml += `<button class="btn btn-sm" onclick="openVehicleSelector()">Change Vehicle</button>`;
  }
  if (status === 'manual') {
    actionsHtml += `<button class="btn btn-sm btn-danger" onclick="removeVehicleSelection()">Remove</button>`;
  }
  if (status === 'unrecognized') {
    actionsHtml += `<button class="btn btn-sm" onclick="openVehicleSelector()">Select Vehicle</button>`;
  }
  actionsEl.innerHTML = actionsHtml;

  renderVehicleList();
}

function renderVehicleList() {
  if (!vehiclePlatforms) return;
  const container = document.getElementById('vehicle-list');
  const query = (document.getElementById('vehicle-search')?.value || '').toLowerCase();

  const makes = {};
  Object.entries(vehiclePlatforms).forEach(([name, data]) => {
    if (query && !name.toLowerCase().includes(query) && !(data.make || '').toLowerCase().includes(query) && !(data.model || '').toLowerCase().includes(query)) {
      return;
    }
    const make = data.make || 'Other';
    if (!makes[make]) makes[make] = [];
    makes[make].push({ name, ...data });
  });

  let html = '';
  const sortedMakes = Object.keys(makes).sort();
  sortedMakes.forEach(make => {
    html += `<div class="vehicle-make-group">`;
    html += `<div class="vehicle-make-header">${make}</div>`;
    makes[make].forEach(p => {
      const isCurrent = vehicleData?.platform_bundle?.name === p.name;
      html += `<div class="vehicle-item ${isCurrent ? 'current' : ''}" onclick="selectVehicle('${p.name.replace(/'/g, "\\'")}')">
        <div class="vehicle-item-name">${p.name}</div>
        <div class="vehicle-item-meta">${(p.year || []).join(', ')} ${p.package ? '— ' + p.package : ''}</div>
        ${isCurrent ? '<span class="current-badge">Current</span>' : ''}
      </div>`;
    });
    html += `</div>`;
  });

  if (!html) {
    html = '<p style="color:var(--text-dim);padding:1rem">No vehicles match your search</p>';
  }
  container.innerHTML = html;
}

const filterVehicles = debounce(() => renderVehicleList(), 200);

function clearVehicleSearch() {
  const inp = document.getElementById('vehicle-search');
  if (inp) inp.value = '';
  renderVehicleList();
  toggleSearchClear('vehicle');
}

function openVehicleSelector() {
  document.getElementById('vehicle-current').style.display = 'none';
  document.getElementById('vehicle-selector').style.display = 'block';
  clearVehicleSearch();
  if (!vehiclePlatforms) {
    api('/api/vehicle/platforms').then(p => { vehiclePlatforms = p; renderVehicleList(); });
  }
}

function closeVehicleSelector() {
  document.getElementById('vehicle-selector').style.display = 'none';
  document.getElementById('vehicle-current').style.display = 'block';
}

async function selectVehicle(platformName) {
  const vehicle = vehiclePlatforms[platformName];
  if (!vehicle) return;

  const isOffroad = vehicleData?.is_offroad;
  const offroadMsg = isOffroad
    ? 'This setting will take effect immediately.'
    : 'This setting will take effect once the device enters offroad state.';

  showModal('Confirm Vehicle Selection',
    `<p><b>${platformName}</b></p><p>${offroadMsg}</p>`,
    [
      { label: 'Cancel', cls: '' },
      { label: 'Confirm', action: `doSelectVehicle('${platformName.replace(/'/g, "\\'")}')`, cls: 'btn-primary' },
    ]
  );
}

async function doSelectVehicle(platformName) {
  try {
    await api('/api/vehicle/select', { method: 'POST', body: JSON.stringify({ platform: platformName }) });
    toast(`Selected ${platformName}`, 'success');
    closeVehicleSelector();
    loadVehicle();
  } catch (e) {
    toast(`Failed to select vehicle: ${e.message}`, 'error');
  }
}

async function removeVehicleSelection() {
  showModal('Remove Vehicle Selection', '<p>This will remove the manual vehicle selection and revert to auto-detection.</p>', [
    { label: 'Cancel', cls: '' },
    { label: 'Remove', action: 'doRemoveVehicleSelection()', cls: 'btn-danger' },
  ]);
}

async function doRemoveVehicleSelection() {
  try {
    await api('/api/vehicle/select', { method: 'DELETE' });
    toast('Vehicle selection removed', 'success');
    loadVehicle();
  } catch (e) {
    toast(`Failed to remove: ${e.message}`, 'error');
  }
}

/* ============ MAPS ============ */
let mapsData = null;
let mapsCountries = null;
let mapsStates = null;

async function loadMaps() {
  try {
    const [status, countries, states] = await Promise.all([
      api('/api/osm/status'),
      mapsCountries ? Promise.resolve(mapsCountries) : api('/api/osm/countries'),
      mapsStates ? Promise.resolve(mapsStates) : api('/api/osm/states'),
    ]);
    mapsData = status;
    if (!mapsCountries) mapsCountries = countries;
    if (!mapsStates) mapsStates = states;
    renderMapsUI();
    pollMapProgress();
  } catch (e) {
    document.getElementById('map-version').textContent = 'Error loading';
  }
}

function renderMapsUI() {
  if (!mapsData) return;

  document.getElementById('map-version').textContent = mapsData.version || 'Unknown';

  const sizeBytes = mapsData.size_bytes || 0;
  let sizeText = '0 B';
  if (sizeBytes >= 1024 * 1024 * 1024) {
    sizeText = (sizeBytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
  } else if (sizeBytes >= 1024 * 1024) {
    sizeText = (sizeBytes / (1024 * 1024)).toFixed(2) + ' MB';
  }
  document.getElementById('map-size').textContent = sizeText;

  renderCountryList();

  if (mapsData?.country === 'US') {
    document.getElementById('map-state-section').style.display = '';
    renderStateList();
  } else {
    document.getElementById('map-state-section').style.display = 'none';
  }

  if (mapsData.last_checked) {
    const dt = new Date(mapsData.last_checked * 1000);
    document.getElementById('map-last-checked').textContent = dt.toLocaleString();
  } else {
    document.getElementById('map-last-checked').textContent = 'Never';
  }

  updateMapProgress();
}

function countryFlag(code) {
  if (!code || code.length !== 2) return '';
  const OFFSET = 0x1F1E6 - 65;
  return String.fromCodePoint(code.charCodeAt(0) + OFFSET, code.charCodeAt(1) + OFFSET);
}

function renderCountryList() {
  const container = document.getElementById('map-country-list');
  if (!container) return;
  if (!mapsCountries) { container.innerHTML = '<p style="color:var(--text-dim)">No countries available.</p>'; return; }

  const query = document.getElementById('map-country-search').value.toLowerCase().trim();
  const active = mapsData?.country || '';
  const hasMaps = mapsData?.size_bytes > 0;

  const sorted = Object.entries(mapsCountries)
    .map(([code, data]) => ({ code, full_name: data.full_name }))
    .sort((a, b) => {
      if (a.code === active && hasMaps) return -1;
      if (b.code === active && hasMaps) return 1;
      return a.full_name.localeCompare(b.full_name);
    });

  const filtered = !query ? sorted
    : sorted.filter(c => c.full_name.toLowerCase().includes(query) || c.code.toLowerCase().includes(query));

  if (!filtered.length) {
    container.innerHTML = '<p style="color:var(--text-dim)">No matching countries.</p>';
    return;
  }

  container.innerHTML = filtered.map(c => {
    const isActive = c.code === active && hasMaps;
    const flag = countryFlag(c.code);
    return `<div class="model-item map-item ${isActive ? 'selected' : ''}">
      <div class="model-item-info">
        <div class="model-item-name"><span class="map-flag">${flag}</span> ${c.full_name}</div>
        <div class="model-item-meta">${c.code}</div>
      </div>
      <div class="model-item-actions">
        ${isActive
          ? `<button class="btn btn-sm btn-danger" onclick="deleteMapCountry()">Delete</button>`
          : `<button class="btn btn-sm btn-primary" onclick="downloadCountry('${c.code}')">Download</button>`
        }
      </div>
    </div>`;
  }).join('');
}

function downloadCountry(code) {
  if (code === 'US') {
    document.getElementById('map-state-section').style.display = '';
    renderStateList();
    document.getElementById('map-state-search').focus();
    toast('Select a state below to download', 'info');
    return;
  }
  showModal('Download Map',
    '<p>Download offline map data for this region? This might take a while.</p>',
    [
      { label: 'Cancel', cls: '' },
      { label: 'Start', action: `doDownloadCountry('${code}')`, cls: 'btn-primary' },
    ]
  );
}

async function doDownloadCountry(code) {
  try {
    await api('/api/osm/select', { method: 'POST', body: JSON.stringify({ country: code, state: null }) });
    await api('/api/osm/download', { method: 'POST' });
    toast('Map download started', 'success');
    loadMaps();
  } catch (e) {
    toast(`Failed: ${e.message}`, 'error');
  }
}

function filterMapCountries() {
  toggleSearchClear('map-country');
  renderCountryList();
}

function clearMapCountrySearch() {
  document.getElementById('map-country-search').value = '';
  document.getElementById('map-country-search-clear').classList.remove('visible');
  renderCountryList();
}

function renderStateList() {
  const container = document.getElementById('map-state-list');
  if (!container) return;
  if (!mapsStates) { container.innerHTML = '<p style="color:var(--text-dim)">No states available.</p>'; return; }

  const query = document.getElementById('map-state-search').value.toLowerCase().trim();
  const activeState = mapsData?.state || '';
  const hasMaps = mapsData?.size_bytes > 0;

  const sorted = Object.entries(mapsStates)
    .map(([code, data]) => ({ code, full_name: data.full_name }))
    .sort((a, b) => {
      if (a.code === activeState && hasMaps) return -1;
      if (b.code === activeState && hasMaps) return 1;
      return a.full_name.localeCompare(b.full_name);
    });

  const filtered = !query ? sorted
    : sorted.filter(s => s.full_name.toLowerCase().includes(query) || s.code.toLowerCase().includes(query));

  if (!filtered.length) {
    container.innerHTML = '<p style="color:var(--text-dim)">No matching states.</p>';
    return;
  }

  container.innerHTML = filtered.map(s => {
    const isActive = s.code === activeState && hasMaps;
    return `<div class="model-item map-item ${isActive ? 'selected' : ''}">
      <div class="model-item-info">
        <div class="model-item-name">${s.full_name}</div>
        <div class="model-item-meta">${s.code}</div>
      </div>
      <div class="model-item-actions">
        ${isActive
          ? `<button class="btn btn-sm btn-danger" onclick="deleteMapCountry()">Delete</button>`
          : `<button class="btn btn-sm btn-primary" onclick="downloadState('${s.code}')">Download</button>`
        }
      </div>
    </div>`;
  }).join('');
}

function downloadState(code) {
  showModal('Download Map',
    '<p>Download offline map data for this state? This might take a while.</p>',
    [
      { label: 'Cancel', cls: '' },
      { label: 'Start', action: `doDownloadState('${code}')`, cls: 'btn-primary' },
    ]
  );
}

async function doDownloadState(code) {
  try {
    await api('/api/osm/select', { method: 'POST', body: JSON.stringify({ country: 'US', state: code }) });
    await api('/api/osm/download', { method: 'POST' });
    toast('Map download started', 'success');
    loadMaps();
  } catch (e) {
    toast(`Failed: ${e.message}`, 'error');
  }
}

function filterMapStates() {
  toggleSearchClear('map-state');
  renderStateList();
}

function clearMapStateSearch() {
  document.getElementById('map-state-search').value = '';
  document.getElementById('map-state-search-clear').classList.remove('visible');
  renderStateList();
}

function deleteMapCountry() {
  showModal('Delete Maps',
    '<p>Delete all downloaded offline map data?</p>',
    [
      { label: 'Cancel', cls: '' },
      { label: 'Delete', action: 'doDeleteMapCountry()', cls: 'btn-danger' },
    ]
  );
}

async function doDeleteMapCountry() {
  try {
    await api('/api/osm/delete', { method: 'POST' });
    toast('Maps deleted', 'success');
    loadMaps();
  } catch (e) {
    toast(`Failed to delete: ${e.message}`, 'error');
  }
}

let mapProgressInterval = null;

function stopMapProgressPoll() {
  if (mapProgressInterval) { clearInterval(mapProgressInterval); mapProgressInterval = null; }
}

function pollMapProgress() {
  if (!mapsData?.downloading) return;
  if (mapProgressInterval) return;
  mapProgressInterval = setInterval(async () => {
    try {
      const status = await api('/api/osm/status');
      mapsData = status;
      updateMapProgress();
      if (!mapsData?.downloading) stopMapProgressPoll();
    } catch {}
  }, 2000);
}

function updateMapProgress() {
  const progressSection = document.getElementById('map-progress');
  const progressFill = document.getElementById('map-progress-fill');
  const progressText = document.getElementById('map-progress-text');
  const downloadSection = document.getElementById('map-download-section');

  if (mapsData?.downloading) {
    progressSection.style.display = 'block';
    downloadSection.style.display = 'none';

    const progress = mapsData.progress || {};
    const total = progress.total_files || 0;
    const done = progress.downloaded_files || 0;
    let pct = 0;
    if (total > 0) pct = Math.round((done / total) * 100);

    progressFill.style.width = pct + '%';
    progressText.textContent = `${pct}% (${done}/${total} files)`;

    pollMapProgress();
  } else {
    progressSection.style.display = 'none';
    downloadSection.style.display = 'block';
  }
}

/* ============ PARAMS ============ */
let allParams = [];
let paramsMetadata = {};

async function loadParams() {
  const container = document.getElementById('params-list');
  try {
    const meta = await api('/api/params');
    paramsMetadata = meta;
    allParams = Object.keys(meta).sort();
    renderParams();
  } catch (e) {
    container.innerHTML = '<p>Could not load params.</p>';
  }
}

function renderParams() {
  const query = (document.getElementById('param-search').value || '').toLowerCase();
  const filtered = allParams.filter(k => k.toLowerCase().includes(query));
  document.getElementById('param-count').textContent = `${filtered.length} / ${allParams.length}`;
  const container = document.getElementById('params-list');
  if (!filtered.length) {
    container.innerHTML = '<p style="color:var(--text-dim)">No matching params.</p>';
    return;
  }
  let html = '';
  for (const key of filtered.slice(0, 500)) {
    html += `
      <div class="param-row">
        <span class="key">${key}</span>
        <span class="val" id="pv-${key}">—</span>
        <button class="edit-btn" onclick="showParamEditor('${key}')">edit</button>
      </div>`;
  }
  container.innerHTML = html;
  for (const key of filtered.slice(0, 500)) {
    api(`/api/params/${key}`, { silent: true }).then(p => {
      const el = document.getElementById(`pv-${key}`);
      if (el) el.textContent = fmtVal(p.value);
    }).catch(() => {});
  }
}

const filterParams = debounce(() => renderParams(), 200);

async function showParamEditor(key) {
  try {
    const p = await api(`/api/params/${key}`);
    showModal(`Edit: ${key}`,
      `<div class="param-editor-body">
        <div class="param-editor-key">${key}</div>
        <textarea id="param-edit-input" class="param-edit-input" rows="4">${p.value || ''}</textarea>
      </div>`,
      [
        { label: 'Cancel', cls: '' },
        { label: 'Save', action: `saveParamFromModal('${key}')`, cls: 'btn-primary' },
      ]
    );
  } catch (e) {}
}

async function saveParamFromModal(key) {
  const inp = document.getElementById('param-edit-input');
  if (!inp) return;
  try {
    await api(`/api/params/${key}`, { method: 'POST', body: JSON.stringify({ value: inp.value }) });
    toast(`Updated ${key}`, 'success');
    renderParams();
  } catch (e) { toast(`Failed to update ${key}`, 'error'); }
}

/* ============ BACKUP ============ */
async function loadBackups() {
  const container = document.getElementById('backup-list');
  try {
    const backups = await api('/api/backup');
    if (!backups.length) {
      container.innerHTML = '<p style="color:var(--text-dim)">No backups found.</p>';
      return;
    }
    let html = '';
    for (const b of backups) {
      const date = new Date(b.mtime * 1000).toLocaleString();
      const size = fmtSize(b.size);
      const label = b.label || '';
      html += `
        <div class="backup-item${label ? ' has-label' : ''}">
          <div class="info">
            <div class="name">${label ? `${escHtml(label)} <span class="backup-fname">${b.name}</span>` : b.name}</div>
            <div class="meta">${date} &middot; ${size}</div>
          </div>
          <div class="backup-actions-row">
            <button class="btn btn-sm" onclick="setBackupLabel('${b.name}')">Label</button>
            <button class="btn btn-download btn-sm" onclick="downloadBackup('${b.name}')">Download</button>
            <button class="btn btn-primary btn-sm" onclick="restoreBackup('${b.name}')">Restore</button>
            <button class="btn btn-danger btn-sm" onclick="deleteBackup('${b.name}')">Delete</button>
          </div>
        </div>`;
    }
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = '<p style="color:var(--text-dim)">Could not load backups.</p>';
  }
}

function uploadBackup() {
  document.getElementById('backup-file-input').click();
}

async function onBackupFileSelected(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file, file.name);
  try {
    const res = await api('/api/backup/upload', { method: 'POST', body: formData });
    toast('Backup uploaded: ' + res.name, 'success');
    loadBackups();
  } catch (e) {
    toast('Upload failed: ' + (e.message || e), 'error');
  }
  event.target.value = '';
}

async function createBackup() {
  try {
    const res = await api('/api/backup/create', { method: 'POST' });
    toast('Backup created: ' + res.name, 'success');
    loadBackups();
  } catch (e) { toast('Backup failed: ' + (e.message || e), 'error'); }
}

async function setBackupLabel(name) {
  showModal('Label Backup', `
    <p>Set a label for <b>${escHtml(name)}</b></p>
    <input type="text" id="backup-label-input" class="param-edit-input" placeholder="My backup label" style="margin-top:0.5rem">
  `, [
    { label: 'Cancel', cls: '' },
    { label: 'Save', action: `doSetBackupLabel('${name}')`, cls: 'btn-primary' },
  ]);
  setTimeout(() => document.getElementById('backup-label-input')?.focus(), 100);
}

async function doSetBackupLabel(name) {
  const input = document.getElementById('backup-label-input');
  const label = input ? input.value.trim() : '';
  try {
    await api(`/api/backup/${encodeURIComponent(name)}/label`, {
      method: 'POST',
      body: JSON.stringify({ label }),
    });
    toast(label ? 'Label saved' : 'Label removed', 'success');
    loadBackups();
  } catch (e) { toast('Failed to save label', 'error'); }
}

async function downloadBackup(name) {
  const a = document.createElement('a');
  a.href = `/api/backup/download/${encodeURIComponent(name)}`;
  a.download = name;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

async function restoreBackup(name) {
  showModal('Restore Backup', `<p>Restore "<b>${name}</b>"?<br>This will overwrite current settings.</p>`, [
    { label: 'Cancel', cls: '' },
    { label: 'Restore', action: `doRestoreBackup('${name}')`, cls: 'btn-primary' },
  ]);
}

async function doRestoreBackup(name) {
  try {
    const res = await api('/api/backup/restore', { method: 'POST', body: JSON.stringify({ name }) });
    toast(`Restored ${res.restored} params`, 'success');
    loadBackups();
  } catch (e) { toast('Restore failed', 'error'); }
}

async function deleteBackup(name) {
  showModal('Delete Backup', `<p>Delete "<b>${name}</b>"? This cannot be undone.</p>`, [
    { label: 'Cancel', cls: '' },
    { label: 'Delete', action: `doDeleteBackup('${name}')`, cls: 'btn-danger' },
  ]);
}

async function doDeleteBackup(name) {
  try {
    await api(`/api/backup/${encodeURIComponent(name)}`, { method: 'DELETE' });
    toast(`Deleted ${name}`, 'success');
    loadBackups();
  } catch (e) { toast('Delete failed', 'error'); }
}

/* ============ LOGS ============ */
let logsData  = [];
let logSource = 'swaglog';
let logLevel  = 0;
let logProc   = '';

async function loadLogs() {
  const searchEl = document.getElementById('log-search');
  const search = searchEl ? searchEl.value.trim() : '';
  const params = new URLSearchParams({ source: logSource, level: logLevel, limit: 500 });
  if (search) params.set('search', search);
  if (logProc && (logSource === 'swaglog' || logSource === 'journal')) params.set('process', logProc);
  const container = document.getElementById('logs-list');
  if (!container) return;
  container.innerHTML = '<p style="color:var(--text-muted)">Loading…</p>';
  try {
    logsData = await api('/api/logs?' + params.toString(), { silent: true });
    renderLogs(logsData);
  } catch (e) {
    container.innerHTML = `<p style="color:var(--red)">Failed to load logs: ${escHtml(e.message || String(e))}</p>`;
  }
}

function renderLogs(entries) {
  const container = document.getElementById('logs-list');
  if (!container) return;
  document.getElementById('log-count').textContent = `${entries.length} entries`;
  if (!entries.length) {
    container.innerHTML = '<p style="color:var(--text-muted)">No entries found.</p>';
    updateProcSelect([]);
    return;
  }
  updateProcSelect(entries);
  container.innerHTML = entries.map(e => {
    const dt = e.ts ? new Date(e.ts * 1000).toLocaleTimeString() : '—';
    const lvl = (e.level || 'INFO').toUpperCase();
    const lvlCls = { DEBUG:'debug', INFO:'info', WARNING:'warn', ERROR:'error', CRITICAL:'crit' }[lvl] || 'info';
    const proc = escHtml(e.process || '');
    if (e.source === 'crash') {
      const msgShort = escHtml((e.msg || '').split('\n').slice(0, 3).join(' ↵ ').slice(0, 200));
      return `<div class="log-row log-crash" onclick="this.classList.toggle('expanded')">
        <div class="log-row-head">
          <span class="log-ts">${dt}</span>
          <span class="log-badge log-badge-crit">CRASH</span>
          <span class="log-proc">${escHtml(e.filename || '')}</span>
          <span class="log-msg">${msgShort}</span>
        </div>
        <pre class="log-crash-body">${escHtml(e.msg || '')}</pre>
      </div>`;
    }
    const msgShort = escHtml((e.msg || '').slice(0, 300));
    return `<div class="log-row">
      <span class="log-ts">${dt}</span>
      <span class="log-badge log-badge-${lvlCls}">${lvl}</span>
      <span class="log-proc">${proc}</span>
      <span class="log-msg">${msgShort}</span>
    </div>`;
  }).join('');
}

function updateProcSelect(entries) {
  const sel = document.getElementById('log-proc-select');
  if (!sel) return;
  const cur = sel.value;
  const procs = [...new Set(entries.map(e => e.process).filter(Boolean))].sort();
  sel.innerHTML = '<option value="">All services</option>' +
    procs.map(p => `<option value="${escHtml(p)}"${p === cur ? ' selected' : ''}>${escHtml(p)}</option>`).join('');
}

function onLogProcChange() {
  logProc = (document.getElementById('log-proc-select')?.value || '').trim();
  loadLogs();
}

const onLogSearch = debounce(() => loadLogs(), 350);

/* Source / level button wiring */
(function initLogToolbar() {
  const srcWrap = document.getElementById('log-sources');
  const lvlWrap = document.getElementById('log-levels');
  if (srcWrap) {
    srcWrap.addEventListener('click', e => {
      const btn = e.target.closest('.log-src-btn');
      if (!btn) return;
      srcWrap.querySelectorAll('.log-src-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      logSource = btn.dataset.src;
      const showLevel = logSource === 'swaglog' || logSource === 'pitstop';
      const showProc  = logSource === 'swaglog' || logSource === 'journal';
      if (lvlWrap) lvlWrap.style.display = showLevel ? '' : 'none';
      const procWrap = document.getElementById('log-proc-wrap');
      if (procWrap) procWrap.style.display = showProc ? '' : 'none';
      logProc = '';
      const sel = document.getElementById('log-proc-select');
      if (sel) sel.value = '';
      loadLogs();
    });
  }
  if (lvlWrap) {
    lvlWrap.addEventListener('click', e => {
      const btn = e.target.closest('.log-lvl-btn');
      if (!btn) return;
      lvlWrap.querySelectorAll('.log-lvl-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      logLevel = parseInt(btn.dataset.level, 10) || 0;
      loadLogs();
    });
  }
})();

/* ============ THEME ============ */
const THEMES = ['dark', 'light', 'hc'];
const THEME_ICONS = { dark: '☾', light: '☀', hc: '◈' };
const THEME_LABELS = { dark: 'Dark', light: 'Light', hc: 'High Contrast' };

function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  const btn = document.getElementById('theme-cycle-btn');
  if (btn) {
    btn.textContent = THEME_ICONS[t];
    btn.title = `Theme: ${THEME_LABELS[t]} — tap to cycle`;
  }
}

function cycleTheme() {
  const current = document.documentElement.dataset.theme || 'dark';
  const next = THEMES[(THEMES.indexOf(current) + 1) % THEMES.length];
  localStorage.setItem('pitstop_theme', next);
  applyTheme(next);
}

/* ---------- Init ---------- */
(function restoreSettings() {
  const theme = localStorage.getItem('pitstop_theme') || 'dark';
  applyTheme(theme);

  /* Auto-refresh defaults to Off; only restore if explicitly saved */
  const saved = localStorage.getItem('pitstop_refresh_v2');
  const sel = document.getElementById('refresh-interval-select');
  if (sel && saved && saved !== '0') {
    ensureSelectOption(sel, saved);
    setAutoRefresh(saved);
  }
  /* Font scale */
  const fs = localStorage.getItem('pitstop_font_scale');
  if (fs) adjFont(0);
})();

/* Restore last active tab on refresh */
const lastPage = localStorage.getItem('pitstop_last_page') || 'dashboard';
navigateTo(lastPage);
