/* Cases + Feedback page */
let _currentCase = null;

async function loadCases() {
  try {
    const cases = await api.cases();
    const el = document.getElementById('cases-list'); if (!el) return;
    if (!cases.length) {
      el.innerHTML = `<div class="empty"><div class="empty-icon">📂</div><div class="empty-title">No Cases</div><div class="empty-sub">Create one or go to Alerts and click + Case</div></div>`;
      return;
    }
    el.innerHTML = cases.map(c => `
      <div class="case-item ${_currentCase?.id===c.id?'active':''}" onclick="selectCase('${c.id}')">
        <div class="case-id">${c.id}</div>
        <div class="case-title">${c.title}</div>
        <div class="case-meta">
          ${statusBadge(c.status)}
          <span class="badge ${c.priority==='high'?'bg-high':c.priority==='low'?'bg-low':'bg-medium'}">${c.priority}</span>
          ${c.alert_count ? `<span style="font-family:var(--mono);font-size:9px;color:var(--txt3)">${c.alert_count} alerts</span>` : ''}
        </div>
      </div>`).join('');
  } catch { toast.error('Failed to load cases'); }
}

async function selectCase(id) {
  try {
    _currentCase = await api.case(id);
    renderDetail(_currentCase);
    document.querySelectorAll('.case-item').forEach(el =>
      el.classList.toggle('active', el.querySelector('.case-id')?.textContent === id));
  } catch { toast.error('Failed to load case'); }
}

function renderDetail(c) {
  const el = document.getElementById('case-detail'); if (!el) return;
  el.innerHTML = `
    <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:16px;gap:12px">
      <div>
        <div class="case-id" style="font-size:10px">${c.id}</div>
        <div style="font-size:15px;font-weight:600;color:var(--txt);margin:4px 0 6px">${c.title}</div>
        <div style="font-size:12px;color:var(--txt2);line-height:1.6">${c.description||'No description.'}</div>
      </div>
      <div style="display:flex;flex-direction:column;gap:5px;align-items:flex-end;flex-shrink:0">
        ${statusBadge(c.status)}
        <span class="badge ${c.priority==='high'?'bg-high':c.priority==='low'?'bg-low':'bg-medium'}">${c.priority}</span>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:12px;background:var(--bg-panel);border-radius:var(--r);border:1px solid var(--border);margin-bottom:14px">
      <div><div class="detail-label">Assigned</div><div class="detail-val">${c.assigned_to||'—'}</div></div>
      <div><div class="detail-label">Created</div><div class="detail-val">${fmt.dt(c.created_at)}</div></div>
      <div><div class="detail-label">Updated</div><div class="detail-val">${fmt.dt(c.updated_at)}</div></div>
    </div>
    ${c.tags&&c.tags.length ? `<div style="margin-bottom:10px;display:flex;gap:5px;flex-wrap:wrap">
      ${c.tags.map(t=>`<span style="font-family:var(--mono);font-size:9px;padding:2px 7px;background:var(--bg-panel);border:1px solid var(--border);border-radius:3px;color:var(--txt2)">${t}</span>`).join('')}
    </div>` : ''}
    ${c.notes ? `<div style="margin-bottom:12px;padding:12px;background:var(--bg-panel);border-radius:var(--r);border:1px solid var(--border);font-size:11px;color:var(--txt2);line-height:1.7;white-space:pre-line">${c.notes}</div>` : ''}
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn btn-ghost btn-sm" onclick="editCase()">Edit</button>
      <button class="btn btn-yellow btn-sm" onclick="updateStatus('investigating')">Mark Investigating</button>
      <button class="btn btn-green btn-sm" onclick="updateStatus('resolved')">Resolve</button>
      <button class="btn btn-red btn-sm" onclick="delCase()">Delete</button>
    </div>`;
}

async function updateStatus(status) {
  if (!_currentCase) return;
  try {
    _currentCase = await api.updateCase(_currentCase.id, {status});
    renderDetail(_currentCase);
    loadCases();
    toast.success('Case updated');
    if (status === 'resolved' && typeof awardForAction !== 'undefined') {
      awardForAction('case_completed', `Case ${_currentCase.id} resolved`);
    }
  } catch { toast.error('Update failed'); }
}

function openNewCase() {
  const ov = document.createElement('div'); ov.className = 'overlay';
  ov.innerHTML = `
    <div class="modal">
      <div class="modal-title">New Investigation Case</div>
      <div class="form-group"><label class="form-label">Title</label>
        <input class="form-input" id="nc-title" placeholder="e.g. Suspicious cluster — USR-0042"></div>
      <div class="form-group"><label class="form-label">Description</label>
        <textarea class="form-textarea" id="nc-desc" placeholder="Describe the investigation goal…"></textarea></div>
      <div class="form-group"><label class="form-label">Priority</label>
        <select class="form-select" id="nc-pri">
          <option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option>
        </select></div>
      <div class="form-group"><label class="form-label">Assigned To</label>
        <input class="form-input" id="nc-assign" value="Sr. Analyst"></div>
      <div class="form-group"><label class="form-label">Link Alert IDs (comma-separated, optional)</label>
        <input class="form-input" id="nc-alerts" placeholder="ALT-XXXXXX, ALT-YYYYYY"></div>
      <div class="modal-actions">
        <button class="btn btn-ghost" onclick="this.closest('.overlay').remove()">Cancel</button>
        <button class="btn btn-primary" onclick="createCase()">Create Case</button>
      </div>
    </div>`;
  ov.addEventListener('click', e => { if (e.target === ov) ov.remove(); });
  document.body.appendChild(ov);
}

async function createCase() {
  const title = document.getElementById('nc-title')?.value?.trim();
  if (!title) { toast.error('Title required'); return; }
  const desc     = document.getElementById('nc-desc')?.value?.trim() || '';
  const priority = document.getElementById('nc-pri')?.value || 'medium';
  const assigned = document.getElementById('nc-assign')?.value?.trim() || 'Sr. Analyst';
  const alertStr = document.getElementById('nc-alerts')?.value || '';
  const alert_ids = alertStr.split(',').map(s => s.trim()).filter(Boolean);
  try {
    const c = await api.createCase({title, description:desc, priority, assigned_to:assigned, alert_ids});
    document.querySelector('.overlay')?.remove();
    toast.success('Case created');
    await loadCases();
    selectCase(c.id);
  } catch { toast.error('Failed to create case'); }
}

function editCase() {
  if (!_currentCase) return;
  const c = _currentCase;
  const ov = document.createElement('div'); ov.className = 'overlay';
  ov.innerHTML = `
    <div class="modal">
      <div class="modal-title">Edit — ${c.id}</div>
      <div class="form-group"><label class="form-label">Title</label>
        <input class="form-input" id="ec-title" value="${c.title}"></div>
      <div class="form-group"><label class="form-label">Description</label>
        <textarea class="form-textarea" id="ec-desc">${c.description||''}</textarea></div>
      <div class="form-group"><label class="form-label">Status</label>
        <select class="form-select" id="ec-status">
          ${['open','investigating','resolved','closed'].map(s=>
            `<option value="${s}" ${c.status===s?'selected':''}>${s}</option>`).join('')}
        </select></div>
      <div class="form-group"><label class="form-label">Priority</label>
        <select class="form-select" id="ec-pri">
          ${['low','medium','high'].map(s=>
            `<option value="${s}" ${c.priority===s?'selected':''}>${s}</option>`).join('')}
        </select></div>
      <div class="form-group"><label class="form-label">Investigation Notes</label>
        <textarea class="form-textarea" id="ec-notes" style="min-height:120px" placeholder="Write your investigation findings here…">${c.notes||''}</textarea></div>
      <div class="modal-actions">
        <button class="btn btn-ghost" onclick="this.closest('.overlay').remove()">Cancel</button>
        <button class="btn btn-primary" onclick="saveEdit()">Save</button>
      </div>
    </div>`;
  ov.addEventListener('click', e => { if (e.target === ov) ov.remove(); });
  document.body.appendChild(ov);
}

async function saveEdit() {
  if (!_currentCase) return;
  const title    = document.getElementById('ec-title')?.value?.trim();
  const desc     = document.getElementById('ec-desc')?.value?.trim();
  const status   = document.getElementById('ec-status')?.value;
  const priority = document.getElementById('ec-pri')?.value;
  const notes    = document.getElementById('ec-notes')?.value?.trim();
  try {
    _currentCase = await api.updateCase(_currentCase.id, {title, description:desc, status, priority, notes});
    document.querySelector('.overlay')?.remove();
    toast.success('Case saved');
    renderDetail(_currentCase);
    loadCases();
  } catch { toast.error('Save failed'); }
}

async function delCase() {
  if (!_currentCase || !confirm(`Delete ${_currentCase.id}? This cannot be undone.`)) return;
  try {
    await api.deleteCase(_currentCase.id);
    _currentCase = null;
    document.getElementById('case-detail').innerHTML = `<div class="empty"><div class="empty-icon">◉</div><div class="empty-title">Select a Case</div><div class="empty-sub">Pick from the list or create a new investigation</div></div>`;
    toast.success('Case deleted');
    loadCases();
  } catch { toast.error('Delete failed'); }
}

/* ── Feedback ── */
async function loadFeedback() {
  try {
    const [log, stats] = await Promise.all([api.feedback(), api.feedbackStats()]);
    set('fb-total',   stats.total);
    set('fb-fp',      stats.false_positives);
    set('fb-rate',    stats.fp_rate + '%');
    set('fb-pending', stats.pending_retrain > 0 ? stats.pending_retrain + ' pending' : '');
    renderFbTable(log);
  } catch {}
}

function renderFbTable(items) {
  const tb = document.getElementById('fb-tbody'); if (!tb) return;
  if (!items.length) {
    tb.innerHTML = `<tr><td colspan="7"><div class="empty"><div class="empty-title">No feedback yet</div><div class="empty-sub">Go to Alerts → View → Feedback to submit</div></div></td></tr>`;
    return;
  }
  tb.innerHTML = items.map(f => `
    <tr>
      <td style="color:var(--cyan)">${f.alert_id}</td>
      <td style="color:var(--txt3)">${f.transaction_id}</td>
      <td>${f.analyst}</td>
      <td><span class="badge ${f.label==='false_positive'?'bg-false_positive':'bg-high'}">${f.label.replace('_',' ')}</span></td>
      <td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--txt2)">${f.reason}</td>
      <td style="color:var(--txt3)">${fmt.time(f.created_at)}</td>
      <td><span class="badge ${f.retrain_used?'bg-low':'bg-false_positive'}">${f.retrain_used?'YES':'NO'}</span></td>
    </tr>`).join('');
}

async function triggerRetrain() {
  const btn = document.getElementById('btn-retrain');
  if (btn) { btn.textContent = 'Training…'; btn.disabled = true; }
  try {
    await api.retrain();
    toast.success('Retrain started — models improving in background');
    if (typeof awardForAction !== 'undefined') {
      awardForAction('model_improvement', 'Triggered model retrain with analyst feedback');
    }
    setTimeout(loadFeedback, 3000);
  } catch { toast.error('Retrain failed'); }
  finally { if (btn) { btn.textContent = 'Trigger Retrain'; btn.disabled = false; } }
}

document.addEventListener('DOMContentLoaded', async () => {
  initClock();
  sidebarCounters.init();
  new AlertStream(alert => { sidebarCounters._render(); }, () => {});
  await Promise.all([loadCases(), loadFeedback()]);
  document.getElementById('btn-new-case')?.addEventListener('click', openNewCase);
  document.getElementById('btn-retrain')?.addEventListener('click', triggerRetrain);
  const firstItem = document.querySelector('.case-item');
  if (firstItem) firstItem.click();
  setInterval(loadFeedback, 15000);
});
