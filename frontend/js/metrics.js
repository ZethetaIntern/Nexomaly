/* Metrics / Model Performance page */
async function loadAll() {
  try {
    const [perf, models] = await Promise.all([api.performance(), api.modelMetrics()]);
    renderPerfCards(perf);
    renderModelCards(models);
    renderMetricBars('perf-bars-if', models.find(m => m.model_name === 'isolation_forest') || null);
    renderMetricBars('perf-bars-rf', models.find(m => m.model_name === 'random_forest')    || null);
  } catch(e) { console.error(e); }
}

function renderPerfCards(p) {
  if (!p || !p.total_predictions) return;
  set('m-prec',  (p.precision      * 100).toFixed(1) + '%');
  set('m-rec',   (p.recall         * 100).toFixed(1) + '%');
  set('m-f1',    (p.f1_score       * 100).toFixed(1) + '%');
  set('m-fpr',   (p.fp_rate        * 100).toFixed(1) + '%');
  set('m-dr',    (p.detection_rate * 100).toFixed(1) + '%');
  set('m-tp',    p.true_positives);
  set('m-fp',    p.false_positives);
  set('m-total', p.total_predictions);
}

function renderModelCards(models) {
  const el = document.getElementById('model-cards'); if (!el) return;
  if (!models || !models.length) {
    el.innerHTML = `<div class="empty" style="padding:30px">
      <div class="empty-icon">🤖</div>
      <div class="empty-title">No training runs yet</div>
      <div class="empty-sub">Upload a CSV dataset or click "Train Models Now" to generate real metrics</div>
    </div>`;
    return;
  }
  el.innerHTML = models.map(m => `
    <div class="panel" style="margin-bottom:12px">
      <div class="panel-hd" style="margin-bottom:8px">
        <span class="panel-title">${m.model_name.replace('_',' ').toUpperCase()}</span>
        <span class="panel-tag">${m.version} · ${m.n_samples.toLocaleString()} samples</span>
      </div>
      <div style="font-size:10px;color:var(--txt3);margin-bottom:12px;font-family:var(--mono)">
        Dataset: ${m.trained_on} · ${fmt.dt(m.created_at)}
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
        ${metricPill('Precision',    m.precision)}
        ${metricPill('Recall',       m.recall)}
        ${metricPill('F1 Score',     m.f1_score)}
        ${metricPill('FP Rate',      m.fp_rate, true)}
        ${metricPill('Det. Rate',    m.detection_rate)}
        ${metricPill('AUC-ROC',      m.auc_roc)}
      </div>
    </div>`).join('');
}

function metricPill(label, val, invert=false) {
  const pct = (val * 100).toFixed(1);
  const color = invert
    ? (val > 0.3 ? 'var(--red)' : val > 0.15 ? 'var(--yellow)' : 'var(--green)')
    : (val > 0.8 ? 'var(--green)' : val > 0.5 ? 'var(--yellow)' : 'var(--red)');
  return `
    <div style="text-align:center;padding:10px 8px;background:var(--bg-panel);border-radius:var(--r);border:1px solid var(--border)">
      <div style="font-family:var(--mono);font-size:18px;font-weight:700;color:${color}">${pct}%</div>
      <div style="font-family:var(--mono);font-size:9px;color:var(--txt3);margin-top:3px;text-transform:uppercase;letter-spacing:.08em">${label}</div>
    </div>`;
}

async function trainNow() {
  const btn = document.getElementById('btn-train');
  if (btn) { btn.textContent = 'Training…'; btn.disabled = true; }
  try {
    await api.trainManual();
    toast.success('Training started — metrics update in ~30 seconds');
    if (typeof awardForAction !== 'undefined') {
      awardForAction('model_improvement', 'Manual model training triggered');
    }
    setTimeout(loadAll, 30000);
  } catch { toast.error('Training failed'); }
  finally { if (btn) { btn.textContent = 'Train Models Now'; btn.disabled = false; } }
}

function initUpload() {
  const zone  = document.getElementById('upload-zone');
  const input = document.getElementById('file-input');
  if (!zone || !input) return;
  zone.addEventListener('click', () => input.click());
  zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag'); });
  zone.addEventListener('dragleave', ()  => zone.classList.remove('drag'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('drag');
    const f = e.dataTransfer.files[0]; if (f) uploadFile(f);
  });
  input.addEventListener('change', () => { if (input.files[0]) uploadFile(input.files[0]); });
}

async function uploadFile(file) {
  if (!file.name.endsWith('.csv')) { toast.error('Only CSV files are supported'); return; }
  const fd = new FormData(); fd.append('file', file);
  const status = document.getElementById('upload-status');
  if (status) status.textContent = 'Uploading…';
  try {
    const r = await fetch(`${BASE}/api/data/upload`, { method:'POST', body:fd });
    if (!r.ok) throw new Error(await r.text());
    const data = await r.json();
    toast.success(`Uploaded: ${data.rows} rows. Training started — refresh in 30s`);
    if (status) status.textContent = `✓ ${data.rows} rows · ${data.columns?.length} columns — training models in background`;
    if (typeof awardForAction !== 'undefined') {
      awardForAction('model_improvement', 'Custom dataset uploaded and training triggered');
    }
    setTimeout(loadAll, 30000);
  } catch(e) {
    toast.error('Upload failed: ' + e.message);
    if (status) status.textContent = 'Upload failed — check file format';
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  initClock();
  sidebarCounters.init();
  new AlertStream(alert => { sidebarCounters._render(); }, () => {});
  initUpload();
  await loadAll();
  document.getElementById('btn-train')?.addEventListener('click', trainNow);
  setInterval(loadAll, 60000);
});
