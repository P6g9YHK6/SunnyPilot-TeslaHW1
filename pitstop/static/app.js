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

function navigateTo(page) {
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`.nav-btn[data-page="${page}"]`)?.classList.add('active');
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page)?.classList.add('active');
  currentPage = page;
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

function loadPage(name) {
  if (name !== 'settings') { stopSettingsStatusPoll(); discardPendingChanges(); }
  if (name !== 'dashboard') stopDashboardPoll();
  if (name !== 'models') stopModelsProgressPoll();
  if (name === 'dashboard') loadDashboard();
  if (name === 'settings') loadSettings();
  if (name === 'models') loadModels();
  if (name === 'params') loadParams();
  if (name === 'backup') loadBackups();
}

function refreshNow() {
  const btn = document.getElementById('refresh-now-btn');
  btn.classList.add('spinning');
  setTimeout(() => btn.classList.remove('spinning'), 600);
  loadPage(currentPage);
}

function setAutoRefresh(seconds) {
  clearInterval(autoRefreshTimer);
  autoRefreshTimer = null;
  const s = parseInt(seconds, 10);
  localStorage.setItem('pitstop_refresh', s);
  if (s > 0) {
    autoRefreshTimer = setInterval(() => loadPage(currentPage), s * 1000);
  }
}

function restartAutoRefresh() {
  const sel = document.getElementById('refresh-interval-select');
  if (sel) setAutoRefresh(sel.value);
}

/* ---------- API helper ---------- */
async function api(path, opts = {}) {
  const silent = opts.silent;
  const fetchOpts = { ...opts };
  delete fetchOpts.silent;
  try {
    const res = await fetch(path, {
      headers: { 'Accept': 'application/json', ...(fetchOpts.body ? { 'Content-Type': 'application/json' } : {}) },
      ...fetchOpts,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || res.statusText);
    }
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) return await res.json();
    return await res.text();
  } catch (e) {
    if (!silent) toast(e.message, 'error');
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

/* ============ DASHBOARD ============ */
let dashboardPollInterval = null;

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
  const dev = t.device || {};
  const standstillBadge = motion.standstill === true ? ' <span class="badge-ign badge-ign-off">STOPPED</span>' : '';
  document.getElementById('card-telemetry').querySelector('.card-body').innerHTML = `
    <div class="row"><span class="label">Ignition</span><span class="value">${ignBadge}</span></div>
    <div class="row"><span class="label">Car</span><span class="value">${car.brand || '—'}</span></div>
    <div class="row"><span class="label">Fingerprint</span><span class="value" style="font-size:0.72rem">${car.fingerprint || '—'}</span></div>
    ${car.vin ? `<div class="row"><span class="label">VIN</span><span class="value" style="font-size:0.72rem">${car.vin}</span></div>` : ''}
    <div class="row"><span class="label">Speed</span><span class="value">${fmtMps(motion.speed_ms)}${standstillBadge}</span></div>
    <div class="row"><span class="label">Gear</span><span class="value">${motion.gear || '—'}</span></div>
    <div class="row"><span class="label">CPU</span><span class="value">${fmtPct(dev.cpu_pct)}</span></div>
    <div class="row"><span class="label">RAM</span><span class="value">${fmtPct(dev.memory_pct)}</span></div>
    <div class="row"><span class="label">Temp</span><span class="value">${fmtTemp(dev.temp_c)}</span></div>
    <div class="row"><span class="label">Free</span><span class="value">${fmtPct(dev.free_space_pct)}</span></div>
    ${dev.network_type ? `<div class="row"><span class="label">Network</span><span class="value">${dev.network_type}</span></div>` : ''}
    ${dev.thermal_status ? `<div class="row"><span class="label">Thermal</span><span class="value">${dev.thermal_status}</span></div>` : ''}
  `;
}

function stopDashboardPoll() {
  clearInterval(dashboardPollInterval);
  dashboardPollInterval = null;
}

async function loadDashboard() {
  stopDashboardPoll();
  try {
    const [device, caps, status, activeModel, telemetry] = await Promise.all([
      api('/api/device'),
      api('/api/capabilities'),
      api('/api/status'),
      api('/api/models/active'),
      api('/api/telemetry', { silent: true }).catch(() => null),
    ]);

    document.getElementById('card-device').querySelector('.card-body').innerHTML = `
      <div class="row"><span class="label">Dongle ID</span><span class="value">${device.dongle_id || '—'}</span></div>
      <div class="row"><span class="label">Serial</span><span class="value">${device.hardware_serial || '—'}</span></div>
      <div class="row"><span class="label">Version</span><span class="value">${device.version || '—'}</span></div>
      <div class="row"><span class="label">Branch</span><span class="value">${device.branch || '—'}</span></div>
      <div class="row"><span class="label">Commit</span><span class="value">${device.git_commit ? device.git_commit.slice(0, 8) : '—'}</span></div>
      <div class="row"><span class="label">Dirty</span><span class="value">${fmtBool(device.is_dirty)}</span></div>
    `;

    document.getElementById('card-capabilities').querySelector('.card-body').innerHTML = `
      <div class="row"><span class="label">Brand</span><span class="value">${caps.brand || '—'}</span></div>
      <div class="row"><span class="label">Device Type</span><span class="value">${caps.device_type || '—'}</span></div>
      <div class="row"><span class="label">Longitudinal</span><span class="value">${fmtBool(caps.has_longitudinal_control)}</span></div>
      <div class="row"><span class="label">Torque Allowed</span><span class="value">${fmtBool(caps.torque_allowed)}</span></div>
      <div class="row"><span class="label">Steer Type</span><span class="value">${caps.steer_control_type || '—'}</span></div>
      <div class="row"><span class="label">ICBM</span><span class="value">${fmtBool(caps.has_icbm)}</span></div>
    `;

    document.getElementById('card-status').querySelector('.card-body').innerHTML = `
      <div class="row"><span class="label">Web UI</span><span class="value">${fmtBool(status.enabled)}</span></div>
      <div class="row"><span class="label">Offroad</span><span class="value">${fmtBool(status.is_offroad)}</span></div>
      <div class="row"><span class="label">Metric</span><span class="value">${fmtBool(status.is_metric)}</span></div>
    `;

    document.getElementById('card-model').querySelector('.card-body').innerHTML = `
      <div class="row"><span class="label">Model</span><span class="value">${activeModel.displayName || activeModel.internalName || '—'}</span></div>
      <div class="row"><span class="label">Runner</span><span class="value">${activeModel.runner !== undefined ? fmtRunner(activeModel.runner) : 'Stock'}</span></div>
    `;

    renderTelemetryCard(telemetry);

    dashboardPollInterval = setInterval(async () => {
      try {
        const t = await api('/api/telemetry', { silent: true });
        renderTelemetryCard(t);
      } catch {}
    }, 2000);
  } catch (e) {
    document.querySelectorAll('#card-device .card-body, #card-capabilities .card-body, #card-status .card-body, #card-model .card-body')
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

/* ---- Pending changes queue ---- */
let pendingChanges = {};
// shape: { [key]: { oldValue, newValue, label, needsCycle } }

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
  succeeded.forEach(r => { delete pendingChanges[r.value]; });
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
  if (t === 'not_engaged') return !status.is_offroad;
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
    { label: 'OK', action: 'nmConfirm', cls: 'btn-primary' },
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

/* ---- Render a single setting item ---- */
let _descId = 0;
function renderSettingItem(item, caps, paramCache, status, depth, forceDisabled = false) {
  const key = item.key || '';
  const title = buildTitle(item, paramCache);
  const desc = item.description || '';
  const widget = item.widget || 'toggle';
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

  } else if (widget === 'info') {
    controlHtml = `<span class="info-display">${fmtVal(paramCache[key])}</span>`;

  } else if (widget === 'button') {
    controlHtml = `<button class="action-btn" data-param="${key}" ${!enabled ? 'disabled' : ''}>${item.action || title}</button>`;

  } else {
    controlHtml = `<span class="item-value-mono">${fmtVal(paramCache[key])}</span>`;
  }

  const extraClasses = `${!enabled && !isBlocked ? 'disabled' : ''} ${isBlocked ? 'blocked' : ''}`;
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

  let html = `<div class="section-item ${extraClasses}"${indentStyle}>`;
  html += `<div class="item-info"><div class="item-title">${title}${detailBtn}${needsCycle}${offroadOnly}${blockedBadge}</div>${descHtml}</div>`;
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
      if (s.is_offroad !== settingsStatus.is_offroad || s.is_metric !== settingsStatus.is_metric) {
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

    renderSettingsUI();
  } catch (e) {
    container.innerHTML = '<p>Could not load settings schema.</p>';
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
    offroadBanner.innerHTML = '&#9989; Offroad &mdash; all settings available';
  } else {
    offroadBanner.className = 'offroad-banner offroad-banner-off';
    offroadBanner.innerHTML = '&#128664; Onroad &mdash; <span class="badge-offroad">Offroad</span> settings are locked';
  }

  function subPanelVisible(sub) {
    if (!sub.trigger_key) return true;
    const val = pc[sub.trigger_key];
    if (sub.trigger_condition === undefined) return val === '1' || val === true;
    if (sub.trigger_condition && typeof sub.trigger_condition === 'object')
      return evaluateRule(sub.trigger_condition, caps, pc, st);
    return String(val) === String(sub.trigger_condition);
  }

  let html = '';
  for (const panel of schema.panels || []) {
    if (!evaluateRules(panel.visibility, caps, pc, st)) continue;
    html += `<div class="panel"><div class="panel-header">${panel.label}</div>`;
    for (const section of panel.sections || []) {
      if (!evaluateRules(section.visibility, caps, pc, st)) continue;
      const sectionEnabled = evaluateRules(section.enablement, caps, pc, st);
      html += `<div class="panel-section">`;
      if (section.title) html += `<div class="section-title">${section.title}</div>`;
      if (section.description) html += `<div class="section-desc">${section.description}</div>`;
      html += renderSubItems(section.items, caps, pc, st, 0, !sectionEnabled);
      for (const sub of section.sub_panels || []) {
        if (!subPanelVisible(sub)) continue;
        if (sub.title || sub.label) html += `<div class="section-title">${sub.title || sub.label}</div>`;
        html += renderSubItems(sub.items, caps, pc, st, 0, !sectionEnabled);
      }
      html += `</div>`;
    }
    html += `</div>`;
  }

  /* vehicle_settings: filter by current car brand if capability data available */
  const carBrand = (caps.brand || '').toLowerCase();
  for (const [brand, vs] of Object.entries(schema.vehicle_settings || {})) {
    if (carBrand && brand.toLowerCase() !== carBrand) continue;
    const items = vs.items || vs;
    if (!items || !items.length) continue;
    html += `<div class="panel"><div class="panel-header">Vehicle Settings: ${brand}</div>`;
    html += `<div class="panel-section">`;
    html += renderSubItems(items, caps, pc, st, 0);
    html += `</div></div>`;
  }

  container.innerHTML = html;

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
      const actionLabel = isCached ? 'Select' : 'Download';
      const actionCls   = isCached ? 'btn-primary' : 'btn-download';
      html += `<div class="model-item">
        <div class="model-item-info">
          <div class="model-item-name">${b.displayName || b.internalName}</div>
          <div class="model-item-meta">Gen ${b.generation || '?'} &middot; ${b.environment || '—'} &middot; ${fmtRunner(b.runner)}${b.is20hz ? ' &middot; 20Hz' : ''}${isCached ? ' &middot; <span class="meta-cached">cached</span>' : ''}</div>
        </div>
        <div class="model-item-actions">
          <button class="fav-btn ${isFav ? 'active' : ''}" onclick="toggleFav('${b.ref}', this)" title="Favorite">${isFav ? '★' : '☆'}</button>
          ${isActive ? '<span class="model-badge active-model">Active</span>' : `<button class="btn btn-sm ${actionCls}" onclick="selectModel(${b.index}, '${(b.displayName || b.internalName).replace(/'/g,"\\'")}', ${isCached})">${actionLabel}</button>`}
        </div>
      </div>`;
    });
    html += `</div>`;
  });

  container.innerHTML = html;
}

const filterModels = debounce(() => {
  if (!modelsData) return;
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
    if (!progress || progress.status === 'no_data') {
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
    let html = '';
    let allDone = true;
    allModels.forEach(m => {
      const dp = m.artifact && m.artifact.downloadProgress;
      const mp = m.metadata && m.metadata.downloadProgress;
      [dp, mp].forEach((p, i) => {
        if (!p) return;
        const type = i === 0 ? 'Artifact' : 'Metadata';
        const pct = p.progress || 0;
        const eta = p.eta || 0;
        const status = p.status;
        const statusText = fmtDownloadStatus(status);
        const isFailed = status === 4;
        const isDone = status >= 2;
        const isCached = status === 3;
        if (!isDone) allDone = false;
        let fillCls = '';
        if (isDone) fillCls = isCached ? ' cached' : (isFailed ? ' failed' : ' done');
        html += `<div class="progress-item">
          <div class="progress-header">
            <span class="progress-type">${m.type !== undefined ? ['Supercombo','Navigation','Vision','Policy','Off-Policy','On-Policy'][m.type]||'Model' : 'Model'} ${i === 0 ? '(model)' : '(meta)'}</span>
            <span class="progress-status">${statusText}${!isDone && !isFailed ? ' ' + pct.toFixed(0) + '% ETA ' + eta + 's' : ''}</span>
          </div>
          <div class="progress-bar"><div class="progress-fill${fillCls}" style="width:${Math.max(pct,2)}%"></div></div>
        </div>`;
      });
    });
    document.getElementById('dl-progress-items').innerHTML = html;

    if (allDone) {
      /* Download complete - reload models after short delay */
      setTimeout(() => { loadModels(); }, 1000);
    }
  } catch {}
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
      html += `
        <div class="backup-item">
          <div class="info">
            <div class="name">${b.name}</div>
            <div class="meta">${date} &middot; ${size}</div>
          </div>
          <div class="backup-actions-row">
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

async function createBackup() {
  try {
    const res = await api('/api/backup/create', { method: 'POST' });
    toast('Backup created: ' + res.name, 'success');
    loadBackups();
  } catch (e) {}
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

  const saved = localStorage.getItem('pitstop_refresh');
  if (saved && saved !== '0') {
    const sel = document.getElementById('refresh-interval-select');
    if (sel) { sel.value = saved; setAutoRefresh(saved); }
  }
})();
loadDashboard();
