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

/* ---------- Formatting ---------- */
function fmtBool(v) { return v ? 'Yes' : 'No'; }
function fmtVal(v) {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'boolean') return fmtBool(v);
  return String(v);
}

/* ============ DASHBOARD ============ */
async function loadDashboard() {
  try {
    const [device, caps, status] = await Promise.all([
      api('/api/device'),
      api('/api/capabilities'),
      api('/api/status'),
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
    `;

    if (status.enabled) {
      setInterval(loadDashboard, 10000);
    }
  } catch (e) {
    document.querySelectorAll('#card-device .card-body, #card-capabilities .card-body, #card-status .card-body')
      .forEach(el => el.textContent = 'Failed to load. Is the server running?');
  }
}

/* ============ SETTINGS ============ */
let settingsSchema = null;

async function loadSettings() {
  const container = document.getElementById('settings-panels');
  try {
    const schema = await api('/api/settings/schema');
    settingsSchema = schema;
    let html = '';
    for (const panel of schema.panels || []) {
      html += `<div class="panel"><div class="panel-header">${panel.label}</div>`;
      for (const section of panel.sections || []) {
        html += `<div class="panel-section">`;
        if (section.title) html += `<div class="section-title">${section.title}</div>`;
        for (const item of section.items || []) {
          html += renderSettingItem(item);
        }
        if (section.sub_panels) {
          for (const sub of section.sub_panels) {
            if (sub.title) html += `<div class="section-title">${sub.title}</div>`;
            for (const subItem of sub.items || []) {
              html += renderSettingItem(subItem);
            }
          }
        }
        html += `</div>`;
      }
      html += `</div>`;
    }
    container.innerHTML = html;

    container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
      cb.addEventListener('change', async (e) => {
        const key = e.target.dataset.param;
        const val = e.target.checked;
        try {
          await api(`/api/params/${key}/bool`, {
            method: 'PUT',
            body: JSON.stringify({ value: val }),
          });
          toast(`Set ${key} = ${val}`, 'success');
        } catch (err) {
          e.target.checked = !val;
        }
      });
    });

    container.querySelectorAll('select').forEach(sel => {
      sel.addEventListener('change', async (e) => {
        const key = e.target.dataset.param;
        const val = e.target.value;
        try {
          await api(`/api/params/${key}`, {
            method: 'POST',
            body: JSON.stringify({ value: val }),
          });
          toast(`Set ${key} = ${val}`, 'success');
        } catch (err) {}
      });
    });

    const keys = new Set();
    container.querySelectorAll('[data-param]').forEach(el => keys.add(el.dataset.param));
    const capsRes = await api('/api/capabilities');
    for (const key of keys) {
      try {
        const param = await api(`/api/params/${key}`);
        const el = container.querySelector(`[data-param="${key}"]`);
        if (!el) continue;
        if (el.type === 'checkbox') {
          el.checked = param.value === '1' || param.value === 'true';
        } else if (el.tagName === 'SELECT') {
          el.value = param.value;
        } else if (el.classList.contains('param-value-display')) {
          el.textContent = fmtVal(param.value);
        }
      } catch (e) {}
    }
  } catch (e) {
    container.innerHTML = '<p>Could not load settings schema. Ensure settings_ui.json exists.</p>';
  }
}

function renderSettingItem(item) {
  const key = item.key || '';
  const title = item.title || key;
  const desc = item.description || '';
  const widget = item.widget || 'toggle';

  if (widget === 'toggle') {
    return `
      <div class="section-item">
        <div class="item-info">
          <div class="item-title">${title}</div>
          ${desc ? `<div class="item-desc">${desc}</div>` : ''}
        </div>
        <label class="toggle">
          <input type="checkbox" data-param="${key}">
          <span class="slider"></span>
        </label>
      </div>`;
  }

  const opts = item.options || [];
  if (widget === 'option' && opts.length) {
    return `
      <div class="section-item">
        <div class="item-info">
          <div class="item-title">${title}</div>
          ${desc ? `<div class="item-desc">${desc}</div>` : ''}
        </div>
        <select data-param="${key}" style="background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:0.35rem 0.6rem;font-size:0.85rem;">
          ${opts.map(o => `<option value="${o.value}">${o.label}</option>`).join('')}
        </select>
      </div>`;
  }

  return `
    <div class="section-item">
      <div class="item-info">
        <div class="item-title">${title}</div>
        ${desc ? `<div class="item-desc">${desc}</div>` : ''}
      </div>
      <span class="param-value-display" data-param="${key}" style="font-family:monospace;font-size:0.8rem;color:var(--text-dim)">—</span>
    </div>`;
}

/* ============ PARAMS ============ */
let allParams = [];
let paramsMetadata = {};

async function loadParams() {
  const container = document.getElementById('params-list');
  try {
    const [meta, _] = await Promise.all([
      api('/api/params'),
      api('/api/device'),
    ]);
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
