/* Dashboard page */
let _feed = [];
const MAX_FEED = 30;

async function loadStats() {
  try {
    const s = await api.dashboard();
    set('s-total',  s.total_alerts_today);
    set('s-high',   s.high_risk_count);
    set('s-cases',  s.open_cases);
    set('s-fp',     s.fp_rate_7d + '%');
    set('s-all',    s.total_alerts_all_time);
    set('s-fb',     s.total_feedback);
    const score = Math.round(s.avg_risk_score);
    set('avg-score', score);
    const color = fmt.scoreColor(score);
    drawGauge('gauge-arc', score, color);
    const gv = document.getElementById('avg-score');
    if (gv) gv.style.color = color;
    setBar('bar-ml',   s.ml_score_avg,          'var(--cyan)');
    setBar('bar-stat', s.statistical_score_avg,  'var(--yellow)');
    setBar('bar-beh',  s.behavioral_score_avg,   'var(--green)');
    set('bar-ml-v',   Math.round(s.ml_score_avg));
    set('bar-stat-v', Math.round(s.statistical_score_avg));
    set('bar-beh-v',  Math.round(s.behavioral_score_avg));
  } catch(e) { console.error('[Stats]', e); }
}

async function loadCharts() {
  try {
    const [h, d] = await Promise.all([api.hourly(), api.dist()]);
    // Convert UTC hours → local time
    const fixed = h.map(point => {
      const utcHour = parseInt(point.hour.split(':')[0]);
      const dt = new Date();
      dt.setUTCHours(utcHour, 0, 0, 0);
      const localH = dt.getHours().toString().padStart(2, '0');
      return { ...point, hour: `${localH}:00` };
    });
    updateTrendChart(fixed);
    updateDistChart(d);
    set('d-high',   d.high   || 0);
    set('d-medium', d.medium || 0);
    set('d-low',    d.low    || 0);
  } catch(e) { console.error('[Charts]', e); }
}

async function loadPerf() {
  try {
    const p = await api.performance();
    if (!p.total_predictions) return;
    set('perf-prec', (p.precision     * 100).toFixed(1) + '%');
    set('perf-rec',  (p.recall        * 100).toFixed(1) + '%');
    set('perf-f1',   (p.f1_score      * 100).toFixed(1) + '%');
    set('perf-fpr',  (p.fp_rate       * 100).toFixed(1) + '%');
    set('perf-dr',   (p.detection_rate* 100).toFixed(1) + '%');
  } catch {}
}

function setBar(id, val, color) {
  const el = document.getElementById(id);
  if (el) { el.style.width = Math.min(Math.round(val), 100) + '%'; el.style.background = color; }
}

function addFeed(alert) {
  _feed.unshift(alert);
  if (_feed.length > MAX_FEED) _feed.pop();
  renderFeed();
}

function _timeAgo(iso) {
  const diff = (Date.now() - new Date(iso + (iso.endsWith('Z') ? '' : 'Z')).getTime()) / 1000;
  if (diff < 10)   return 'just now';
  if (diff < 60)   return Math.round(diff) + 's ago';
  if (diff < 3600) return Math.round(diff/60) + 'm ago';
  return Math.round(diff/3600) + 'h ago';
}

function renderFeed() {
  const el = document.getElementById('live-feed'); if (!el) return;
  if (!_feed.length) {
    el.innerHTML = '<div class="loading"><div class="loading-txt">AWAITING STREAM…</div></div>';
    return;
  }
  el.innerHTML = _feed.slice(0, 12).map(a => `
    <div class="feed-item fi-${a.level}" onclick="window.location.href='investigation.html'">
      <span class="fi-badge ${a.level}">${a.level}</span>
      <div class="fi-body">
        <div class="fi-id">${a.id} · ${a.user_id}</div>
        <div class="fi-reason">${a.reason}</div>
        <div class="fi-meta">${fmt.$(a.amount)} · ${_timeAgo(a.created_at)}</div>
      </div>
      <div class="fi-score" style="color:${fmt.scoreColor(a.risk_score)}">${Math.round(a.risk_score)}</div>
    </div>`).join('');
}

document.addEventListener('DOMContentLoaded', async () => {
  initClock();
  initTrendChart('trend-chart');
  initDistChart('dist-chart');
  sidebarCounters.init();

  await Promise.all([loadStats(), loadCharts(), loadPerf()]);

  try {
    const alerts = await api.alerts({limit: 12});
    _feed = alerts;
    renderFeed();
  } catch {}

  new AlertStream(alert => {
    sidebarCounters._render();
    addFeed(alert);
    loadStats();
    loadCharts();
    triggerShakeAndFlash(alert);
  }, setWsStatus);

  document.getElementById('btn-sim')?.addEventListener('click', async e => {
    e.target.textContent = 'Simulating…'; e.target.disabled = true;
    try { await api.simulate(); toast.success('Alert simulated!'); }
    catch { toast.error('Simulation failed'); }
    finally { e.target.textContent = '+ Simulate Alert'; e.target.disabled = false; }
  });

  setInterval(() => { loadStats(); loadCharts(); }, 9000);
  setInterval(loadPerf, 30000);
  setInterval(renderFeed, 60000);
});
