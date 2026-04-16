/* Alerts / Investigation page */
let _feedItems = [];

async function loadAlerts() {
  const level  = document.getElementById('f-level')?.value  || '';
  const status = document.getElementById('f-status')?.value || '';
  const search = document.getElementById('f-search')?.value?.trim() || '';
  const params = {};
  if (level  && level  !== 'all') params.level  = level;
  if (status && status !== 'all') params.status = status;
  if (search) params.search = search;
  try {
    const data = await api.alerts(params);
    set('f-count', data.length + ' alerts');
    renderTable(data);
  } catch(e) { console.error('[Alerts]', e); }
}

function renderTable(rows) {
  const tb = document.getElementById('alerts-tbody'); if (!tb) return;
  if (!rows.length) {
    tb.innerHTML = `<tr><td colspan="9"><div class="empty"><div class="empty-icon">◎</div><div class="empty-title">No alerts found</div></div></td></tr>`;
    return;
  }
  tb.innerHTML = rows.map(a => `
    <tr>
      <td style="color:var(--cyan)">${a.id}</td>
      <td>${a.user_id}</td>
      <td>${fmt.$(a.amount)}</td>
      <td>
        <div class="sbar-wrap">
          <div class="sbar-track"><div class="sbar-fill" style="width:${a.risk_score}%;background:${fmt.scoreColor(a.risk_score)}"></div></div>
          <span style="font-family:var(--mono);font-size:10px;color:${fmt.scoreColor(a.risk_score)};min-width:24px">${Math.round(a.risk_score)}</span>
        </div>
      </td>
      <td>${levelBadge(a.level)}</td>
      <td>${statusBadge(a.status)}</td>
      <td style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--txt2)">${a.reason}</td>
      <td style="color:var(--txt3)">${fmt.time(a.created_at)}</td>
      <td>
        <div style="display:flex;gap:5px">
          <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();openDetail('${a.id}')">View</button>
          <button class="btn btn-yellow btn-sm" onclick="event.stopPropagation();quickMakeCase('${a.id}','${a.user_id}',${a.risk_score},'${a.level}')">+ Case</button>
        </div>
      </td>
    </tr>`).join('');
}

async function openDetail(id) {
  try {
    const a = await api.alert(id);
    showDetailModal(a);
  } catch { toast.error('Failed to load alert'); }
}

function showDetailModal(a) {
  const ov = document.createElement('div'); ov.className = 'overlay';
  const contribs    = a.feature_contributions || {};
  const topContribs = Object.entries(contribs).slice(0, 8);
  const maxC = topContribs.length ? Math.max(...topContribs.map(([,v]) => v), 1) : 1;

  ov.innerHTML = `
    <div class="modal">
      <div class="modal-title">Alert Detail — ${a.id}</div>
      <div class="detail-grid">
        <div><div class="detail-label">User ID</div><div class="detail-val">${a.user_id}</div></div>
        <div><div class="detail-label">Amount</div><div class="detail-val" style="color:var(--cyan);font-size:16px">${fmt.$(a.amount)}</div></div>
        <div><div class="detail-label">Risk Level</div><div>${levelBadge(a.level)}</div></div>
        <div><div class="detail-label">Status</div><div>${statusBadge(a.status)}</div></div>
        <div style="grid-column:1/-1"><div class="detail-label">Reason</div>
          <div class="detail-val" style="font-size:11px;color:var(--txt2)">${a.reason}</div></div>
      </div>
      <div class="detail-label" style="margin-bottom:8px">Score Breakdown</div>
      <div class="score-rows" style="margin-bottom:14px">
        ${scoreRow('ML Ensemble',     a.ml_score,          'var(--cyan)')}
        ${scoreRow('Isolation Forest',a.isolation_score,   'var(--cyan)')}
        ${scoreRow('Random Forest',   a.rf_score,          'var(--purple)')}
        ${scoreRow('Statistical',     a.statistical_score, 'var(--yellow)')}
        ${scoreRow('Behavioral',      a.behavioral_score,  'var(--green)')}
        ${scoreRow('Ensemble Total',  a.risk_score,        fmt.scoreColor(a.risk_score))}
      </div>
      ${topContribs.length ? `
        <div class="detail-label" style="margin-bottom:8px">Feature Contributions</div>
        <div style="margin-bottom:14px">
          ${topContribs.map(([k,v]) => `
            <div class="contrib-row">
              <span class="contrib-name">${k.replace(/_/g,' ')}</span>
              <div class="contrib-bar-track"><div class="contrib-bar-fill" style="width:${Math.round(v/maxC*100)}%"></div></div>
              <span class="contrib-val">${v.toFixed(1)}</span>
            </div>`).join('')}
        </div>` : ''}
      <div class="form-group">
        <label class="form-label">Update Status</label>
        <select class="form-select" id="modal-status">
          ${['new','reviewing','resolved','false_positive'].map(s =>
            `<option value="${s}" ${a.status===s?'selected':''}>${s.replace('_',' ')}</option>`).join('')}
        </select>
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" onclick="this.closest('.overlay').remove()">Close</button>
        <button class="btn btn-yellow btn-sm" onclick="openFeedback('${a.id}','${a.transaction_id||''}')">Feedback</button>
        <button class="btn btn-ghost btn-sm" onclick="quickMakeCase('${a.id}','${a.user_id}',${a.risk_score},'${a.level}');this.closest('.overlay').remove()">+ Case</button>
        <button class="btn btn-primary" onclick="saveStatus('${a.id}')">Save Status</button>
      </div>
    </div>`;
  ov.addEventListener('click', e => { if (e.target === ov) ov.remove(); });
  document.body.appendChild(ov);
}

function scoreRow(name, val, color) {
  return `<div class="score-row">
    <span class="score-name">${name}</span>
    <div class="bar-track"><div class="bar-fill" style="width:${Math.min(Math.round(val),100)}%;background:${color}"></div></div>
    <span class="score-num">${Math.round(val)}</span>
  </div>`;
}

async function saveStatus(id) {
  const sel = document.getElementById('modal-status'); if (!sel) return;
  try {
    await api.alertStatus(id, sel.value);
    toast.success('Status updated');
    document.querySelector('.overlay')?.remove();
    if (sel.value === 'resolved' && typeof awardForAction !== 'undefined') {
      awardForAction('confirmed_fraud', 'Alert marked as resolved');
    }
    loadAlerts();
  } catch { toast.error('Update failed'); }
}

async function quickMakeCase(alertId, userId, score, level) {
  try {
    const c = await api.createCase({
      title:       `${level.toUpperCase()} alert — ${userId}`,
      description: `Auto-created from alert ${alertId}. Risk score: ${Math.round(score)}. Requires investigation.`,
      priority:    level === 'high' ? 'high' : level === 'medium' ? 'medium' : 'low',
      assigned_to: 'Sr. Analyst',
      alert_ids:   [alertId]
    });
    toast.success(`Case ${c.id} created — go to Cases tab`);
    if (typeof awardForAction !== 'undefined') {
      awardForAction('case_completed', `Case created for alert ${alertId}`);
    }
  } catch { toast.error('Failed to create case'); }
}

function openFeedback(alertId, txId) {
  const ov = document.createElement('div'); ov.className = 'overlay';
  ov.innerHTML = `
    <div class="modal" style="max-width:440px">
      <div class="modal-title">Submit Analyst Feedback</div>
      <div class="form-group">
        <label class="form-label">Alert ID</label>
        <input class="form-input" value="${alertId}" readonly>
      </div>
      <div class="form-group">
        <label class="form-label">Label</label>
        <select class="form-select" id="fb-label">
          <option value="true_positive">True Positive — Confirmed Fraud (+100 XP)</option>
          <option value="false_positive">False Positive — Not Fraud (−50 XP)</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Confidence (0–1)</label>
        <input class="form-input" id="fb-conf" type="number" min="0" max="1" step="0.1" value="1.0">
      </div>
      <div class="form-group">
        <label class="form-label">Reason / Notes</label>
        <textarea class="form-textarea" id="fb-reason" placeholder="e.g. Confirmed fraud — customer reported unauthorized charge"></textarea>
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" onclick="this.closest('.overlay').remove()">Cancel</button>
        <button class="btn btn-primary" onclick="submitFb('${alertId}','${txId}')">Submit</button>
      </div>
    </div>`;
  ov.addEventListener('click', e => { if (e.target === ov) ov.remove(); });
  document.body.appendChild(ov);
}

async function submitFb(alertId, txId) {
  const label  = document.getElementById('fb-label')?.value;
  const reason = document.getElementById('fb-reason')?.value?.trim();
  const conf   = parseFloat(document.getElementById('fb-conf')?.value || '1');
  if (!reason) { toast.error('Please enter a reason'); return; }
  // Fix: always use a valid transaction_id — fallback to alertId
  const safeTxId = (txId && txId !== 'null' && txId !== 'undefined' && txId !== '')
                   ? txId : alertId;
  try {
    await api.submitFeedback({
      alert_id:       alertId,
      transaction_id: safeTxId,
      analyst:        'Sr. Analyst',
      label,
      reason,
      confidence:     conf
    });
    document.querySelector('.overlay')?.remove();
    toast.success('Feedback submitted ✓');
    // Award XP
    if (typeof awardForAction !== 'undefined') {
      const evt  = label === 'true_positive' ? 'confirmed_fraud' : 'false_positive';
      const desc = label === 'true_positive' ? 'Confirmed fraud detection' : 'False positive correction';
      awardForAction(evt, desc);
    }
    loadAlerts();
  } catch(e) {
    console.error('Feedback error:', e);
    toast.error('Submission failed: ' + e.message);
  }
}

function addFeedItem(a) {
  _feedItems.unshift(a);
  if (_feedItems.length > 20) _feedItems.pop();
  const fc = document.getElementById('live-feed'); if (!fc) return;
  const d  = document.createElement('div');
  d.className = `feed-item fi-${a.level}`;
  d.innerHTML = `
    <span class="fi-badge ${a.level}">${a.level}</span>
    <div class="fi-body">
      <div class="fi-id">${a.id} · ${a.user_id}</div>
      <div class="fi-reason">${a.reason}</div>
      <div class="fi-meta">${fmt.$(a.amount)} · just now</div>
    </div>
    <div class="fi-score" style="color:${fmt.scoreColor(a.risk_score)}">${Math.round(a.risk_score)}</div>`;
  fc.insertBefore(d, fc.firstChild);
  while (fc.children.length > 20) fc.removeChild(fc.lastChild);
  loadAlerts();
  loadScores();
}

async function loadScores() {
  try {
    const s = await api.dashboard();
    set('avg-score', Math.round(s.avg_risk_score));
    const color = fmt.scoreColor(s.avg_risk_score);
    if (typeof drawGauge !== 'undefined') drawGauge('gauge-arc', s.avg_risk_score, color);
    const gv = document.getElementById('avg-score');
    if (gv) gv.style.color = color;
    [['bar-ml',s.ml_score_avg,'var(--cyan)'],
     ['bar-stat',s.statistical_score_avg,'var(--yellow)'],
     ['bar-beh',s.behavioral_score_avg,'var(--green)']].forEach(([id,val,c]) => {
      const el = document.getElementById(id);
      if (el) { el.style.width = Math.min(Math.round(val),100)+'%'; el.style.background = c; }
      set(id+'-v', Math.round(val));
    });
  } catch {}
}

document.addEventListener('DOMContentLoaded', async () => {
  initClock();
  sidebarCounters.init();
  await Promise.all([loadAlerts(), loadScores()]);

  // Seed feed from recent alerts
  try {
    const alerts = await api.alerts({limit: 10});
    const fc = document.getElementById('live-feed');
    if (fc && alerts.length) {
      _feedItems = alerts;
      fc.innerHTML = alerts.map(a => `
        <div class="feed-item fi-${a.level}">
          <span class="fi-badge ${a.level}">${a.level}</span>
          <div class="fi-body">
            <div class="fi-id">${a.id} · ${a.user_id}</div>
            <div class="fi-reason">${a.reason}</div>
            <div class="fi-meta">${fmt.$(a.amount)} · ${fmt.time(a.created_at)}</div>
          </div>
          <div class="fi-score" style="color:${fmt.scoreColor(a.risk_score)}">${Math.round(a.risk_score)}</div>
        </div>`).join('');
    }
  } catch {}

  new AlertStream(alert => {
    sidebarCounters._render();
    addFeedItem(alert);
    triggerShakeAndFlash(alert);
  }, setWsStatus);

  ['f-level','f-status'].forEach(id =>
    document.getElementById(id)?.addEventListener('change', loadAlerts));
  document.getElementById('f-search')?.addEventListener('input', () => {
    clearTimeout(window._st);
    window._st = setTimeout(loadAlerts, 350);
  });
  document.getElementById('btn-reset')?.addEventListener('click', () => {
    document.getElementById('f-level').value  = '';
    document.getElementById('f-status').value = '';
    document.getElementById('f-search').value = '';
    loadAlerts();
  });
  document.getElementById('btn-sim')?.addEventListener('click', async e => {
    e.target.textContent = 'Simulating…'; e.target.disabled = true;
    try { await api.simulate(); toast.success('Alert simulated!'); }
    catch { toast.error('Failed'); }
    finally { e.target.textContent = '+ Simulate'; e.target.disabled = false; }
  });

  setInterval(() => { loadAlerts(); loadScores(); }, 10000);
});
