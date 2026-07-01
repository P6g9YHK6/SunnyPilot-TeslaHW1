/* ---------- Navigation ---------- */
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + btn.dataset.page).classList.add('active');
    loadPage(btn.dataset.page);
  });
});

function loadPage(name) {
  if (name === 'dashboard') loadDashboard();
  if (name === 'settings') loadSettings();
  if (name === 'models') loadModels();
  if (name === 'params') loadParams();
  if (name === 'backup') loadBackups();
}

/* ---------- API helper ---------- */
async function api(path, opts = {}) {
  try {
    const res = await fetch(path, {
      headers: { 'Accept': 'application/json', ...(opts.body ? { 'Content-Type': 'application/json' } : {}) },
      ...opts,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || res.statusText);
    }
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) return await res.json();
    return await res.text();
  } catch (e) {
    toast(e.message, 'error');
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
        <div class="modal-actions">${(buttons||[]).map(b => `<button class="btn ${b.cls||''} btn-sm" onclick="(${b.action})();closeModal()">${b.label}</button>`).join('')}</div>
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
async function loadDashboard() {
  try {
    const [device, caps, status, activeModel] = await Promise.all([
      api('/api/device'),
      api('/api/capabilities'),
      api('/api/status'),
      api('/api/models/active'),
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
function renderSettingItem(item, caps, paramCache, status, depth) {
  const key = item.key || '';
  const title = buildTitle(item, paramCache);
  const desc = item.description || '';
  const widget = item.widget || 'toggle';
  const detailBtn = item.details ? `<button class="item-detail-btn" onclick="showModal('${title.replace(/'/g,"\\'")}','<p>${item.details.replace(/'/g,"\\'").replace(/</g,'&lt;').replace(/>/g,'&gt;')}</p>',[{label:'Close',action:'',cls:'btn-primary'}])" title="Details">i</button>` : '';
  const needsCycle = item.needs_onroad_cycle ? '<span class="badge-restart">Restart</span>' : '';
  const isBlocked = !!item.blocked;
  const vis = evaluateRules(item.visibility, caps, paramCache, status);
  const enabled = !isBlocked && evaluateRules(item.enablement, caps, paramCache, status);
  const hasSub = item.sub_items && item.sub_items.length > 0;
  const parentChecked = paramCache[key];

  if (!vis) return '';

  let controlHtml = '';
  const idAttr = `si-${key}`;

  if (widget === 'toggle') {
    const checked = parentChecked === '1' || parentChecked === 'true';
    controlHtml = `<label class="toggle">
      <input type="checkbox" id="${idAttr}" data-param="${key}" ${checked ? 'checked' : ''} ${!enabled ? 'disabled' : ''}>
      <span class="slider"></span>
    </label>`;

  } else if (widget === 'multiple_button') {
    const opts = item.options || [];
    const currentVal = paramCache[key];
    controlHtml = `<div class="segmented-control">`;
    opts.forEach((o, i) => {
      const isActive = String(currentVal) === String(o.value);
      const optEnabled = enabled && evaluateRules(o.enablement, caps, paramCache, status);
      controlHtml += `<button class="segmented-btn ${isActive ? 'active' : ''}" data-param="${key}" data-value="${o.value}" ${!optEnabled ? 'disabled' : ''}>${o.label}</button>`;
    });
    controlHtml += `</div>`;

  } else if (widget === 'option') {
    if (item.options && item.options.length) {
      const currentVal = paramCache[key];
      controlHtml = `<select class="setting-select" data-param="${key}" ${!enabled ? 'disabled' : ''}>`;
      item.options.forEach(o => {
        controlHtml += `<option value="${o.value}" ${String(currentVal) === String(o.value) ? 'selected' : ''}>${o.label}</option>`;
      });
      controlHtml += `</select>`;
    } else {
      const unit = buildUnit(item, status.is_metric);
      controlHtml = `<span style="font-family:monospace;font-size:0.85rem;color:var(--text)">${fmtVal(paramCache[key])}${unit}</span>`;
    }

  } else if (widget === 'info') {
    controlHtml = `<span class="info-display">${fmtVal(paramCache[key])}</span>`;

  } else if (widget === 'button') {
    controlHtml = `<button class="action-btn" data-param="${key}" ${!enabled ? 'disabled' : ''}>${item.action || title}</button>`;

  } else {
    controlHtml = `<span class="item-value" style="font-family:monospace;font-size:0.8rem;color:var(--text-dim)">${fmtVal(paramCache[key])}</span>`;
  }

  const extraClasses = `${!vis ? 'hidden-item' : ''} ${!enabled && !isBlocked ? 'disabled' : ''} ${isBlocked ? 'blocked' : ''}`;
  const indentStyle = depth > 0 ? ` style="padding-left:${1.25 + depth * 1.25}rem"` : '';

  let html = `<div class="section-item ${extraClasses}"${indentStyle}>`;
  html += `<div class="item-info"><div class="item-title">${title}${detailBtn}${needsCycle}</div>${desc ? `<div class="item-desc">${desc}</div>` : ''}</div>`;
  html += `<div class="item-control">${controlHtml}</div>`;
  html += `</div>`;

  return html;
}

/* ---- Render sub_items recursively ---- */
function renderSubItems(items, caps, paramCache, status, depth) {
  if (!items) return '';
  let html = '';
  items.forEach(item => {
    html += renderSettingItem(item, caps, paramCache, status, depth);
    const parentVal = paramCache[item.key];
    const parentOn = parentVal === '1' || parentVal === 'true';
    if (item.sub_items && parentOn) {
      item.sub_items.forEach(sub => {
        html += renderSettingItem(sub, caps, paramCache, status, depth + 1);
      });
    }
  });
  return html;
}

/* ---- Main settings loader ---- */
async function loadSettings() {
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
        const r = await api(`/api/params/${k}`);
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
  let html = '';
  for (const panel of schema.panels || []) {
    if (!evaluateRules(panel.visibility, caps, pc, st)) continue;
    html += `<div class="panel"><div class="panel-header">${panel.label}</div>`;
    for (const section of panel.sections || []) {
      if (!evaluateRules(section.visibility, caps, pc, st)) continue;
      const sectionEnabled = evaluateRules(section.enablement, caps, pc, st);
      html += `<div class="panel-section">`;
      if (section.title) html += `<div class="section-title">${section.title}</div>`;
      html += renderSubItems(section.items, caps, pc, st, 0);
      for (const sub of section.sub_panels || []) {
        if (sub.title) html += `<div class="section-title">${sub.title}</div>`;
        html += renderSubItems(sub.items, caps, pc, st, 0);
      }
      html += `</div>`;
    }
    html += `</div>`;
  }
  container.innerHTML = html;

  /* Wire up toggle events */
  container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', async (e) => {
      const key = e.target.dataset.param;
      const val = e.target.checked;
      try {
        await api(`/api/params/${key}/bool`, { method: 'PUT', body: JSON.stringify({ value: val }) });
        settingsParamCache[key] = val ? '1' : '0';
        maybeReEval();
        toast(`Set ${key} = ${val}`, 'success');
      } catch { e.target.checked = !val; }
    });
  });

  /* Wire up segmented control events (multiple_button) */
  container.querySelectorAll('.segmented-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      if (e.target.disabled) return;
      const key = e.target.dataset.param;
      const val = e.target.dataset.value;
      try {
        await api(`/api/params/${key}`, { method: 'POST', body: JSON.stringify({ value: val }) });
        settingsParamCache[key] = val;
        maybeReEval();
        toast(`Set ${key} = ${val}`, 'success');
      } catch {}
    });
  });

  /* Wire up select events */
  container.querySelectorAll('select.setting-select').forEach(sel => {
    sel.addEventListener('change', async (e) => {
      const key = e.target.dataset.param;
      const val = e.target.value;
      try {
        await api(`/api/params/${key}`, { method: 'POST', body: JSON.stringify({ value: val }) });
        settingsParamCache[key] = val;
        maybeReEval();
        toast(`Set ${key} = ${val}`, 'success');
      } catch {}
    });
  });

  /* Wire up button events */
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
      const models = b.models || [];
      html += `<div class="model-item">
        <div class="model-item-info">
          <div class="model-item-name">${b.displayName || b.internalName}</div>
          <div class="model-item-meta">Gen ${b.generation || '?'} &middot; ${b.environment || '—'} &middot; ${fmtRunner(b.runner)}${b.is20hz ? ' &middot; 20Hz' : ''}</div>
        </div>
        <div class="model-item-actions">
          <button class="fav-btn ${isFav ? 'active' : ''}" onclick="toggleFav('${b.ref}', this)" title="Favorite">${isFav ? '★' : '☆'}</button>
          ${isActive ? '<span class="model-badge active-model">Active</span>' : `<button class="btn btn-sm btn-primary" onclick="selectModel(${b.index}, '${(b.displayName || b.internalName).replace(/'/g,"\\'")}')">Download</button>`}
        </div>
      </div>`;
    });
    html += `</div>`;
  });

  container.innerHTML = html;
}

function filterModels() {
  if (!modelsData) return;
  const query = document.getElementById('model-search').value.toLowerCase();
  const bundles = (modelsData.bundles || []).filter(b =>
    (b.displayName || '').toLowerCase().includes(query) ||
    (b.internalName || '').toLowerCase().includes(query)
  );
  renderBundleList(bundles, modelsData.active, modelsData.favorites);
}

async function refreshModelList() {
  await api('/api/models/refresh', { method: 'POST' });
  toast('Model list refresh triggered', 'info');
  setTimeout(loadModels, 2000);
}

async function selectModel(index, name) {
  showModal('Download Model', `<p>Download "${name}"? This may take a few minutes.</p>`, [
    { label: 'Cancel', action: '', cls: '' },
    { label: 'Download', action: `api('/api/models/select',{method:'POST',body:JSON.stringify({index:${index}})})&&toast('Downloading ${name}','info')`, cls: 'btn-primary' },
  ]);
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
    document.getElementById('model-cache-size').textContent = `${bundles.length} bundles available`;
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
    api(`/api/params/${key}`).then(p => {
      const el = document.getElementById(`pv-${key}`);
      if (el) el.textContent = fmtVal(p.value);
    }).catch(() => {});
  }
}

function filterParams() { renderParams(); }

async function showParamEditor(key) {
  try {
    const p = await api(`/api/params/${key}`);
    const newVal = prompt(`Edit param: ${key}\nCurrent value:`, p.value);
    if (newVal === null) return;
    await api(`/api/params/${key}`, {
      method: 'POST',
      body: JSON.stringify({ value: newVal }),
    });
    toast(`Updated ${key}`, 'success');
    renderParams();
  } catch (e) {}
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
      const size = b.size > 1024 ? (b.size / 1024).toFixed(1) + ' KB' : b.size + ' B';
      html += `
        <div class="backup-item">
          <div class="info">
            <div class="name">${b.name}</div>
            <div class="meta">${date} &middot; ${size}</div>
          </div>
          <button class="btn btn-primary" onclick="restoreBackup('${b.name}')">Restore</button>
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
  if (!confirm(`Restore backup "${name}"? This will overwrite current settings.`)) return;
  try {
    const res = await api('/api/backup/restore', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
    toast(`Restored ${res.restored} params`, 'success');
  } catch (e) {}
}

/* ---------- Init ---------- */
loadDashboard();
