const BASE = window.API_BASE || 'http://localhost:9000';
const WS   = BASE.replace(/^http/, 'ws');

const api = {
  _get: async p => {
    const r = await fetch(BASE + p);
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  },
  _post: async (p, b) => {
    const r = await fetch(BASE + p, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: b ? JSON.stringify(b) : undefined
    });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  },
  _put: async (p, b) => {
    const r = await fetch(BASE + p, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: b ? JSON.stringify(b) : undefined
    });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  },
  _del: async p => {
    const r = await fetch(BASE + p, { method: 'DELETE' });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  },

  alerts:        (params={}) => api._get('/api/alerts' + (Object.keys(params).length ? '?' + new URLSearchParams(params) : '')),
  alert:         id          => api._get(`/api/alerts/${id}`),
  alertStatus:   (id,status) => api._put(`/api/alerts/${id}/status`, {status}),
  simulate:      ()          => api._post('/api/alerts/simulate'),
  dashboard:     ()          => api._get('/api/metrics/dashboard'),
  hourly:        (h=24)      => api._get(`/api/metrics/hourly?hours=${h}`),
  dist:          ()          => api._get('/api/metrics/distribution'),
  performance:   ()          => api._get('/api/metrics/performance'),
  modelMetrics:  ()          => api._get('/api/metrics/models'),
  cases:         ()          => api._get('/api/cases'),
  case:          id          => api._get(`/api/cases/${id}`),
  createCase:    b           => api._post('/api/cases', b),
  updateCase:    (id, b)     => api._put(`/api/cases/${id}`, b),
  deleteCase:    id          => api._del(`/api/cases/${id}`),
  linkAlert:     (cid, aid)  => api._post(`/api/cases/${cid}/alerts/${aid}`),
  feedback:      ()          => api._get('/api/feedback'),
  feedbackStats: ()          => api._get('/api/feedback/stats'),
  submitFeedback:b           => api._post('/api/feedback', b),
  retrain:       ()          => api._post('/api/feedback/retrain'),
  datasets:      ()          => api._get('/api/data/datasets'),
  trainManual:   ()          => api._post('/api/data/train'),
  health:        ()          => api._get('/api/health'),
};

/* ── WebSocket live stream ── */
class AlertStream {
  constructor(onAlert, onStatus) {
    this.onAlert  = onAlert;
    this.onStatus = onStatus;
    this.ws       = null;
    this.delay    = 2000;
    this.stopped  = false;
    this.connect();

    // Reconnect when tab becomes visible again
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
          this.connect();
        }
      }
    });

    // Health check every 5s
    setInterval(() => {
      if (!this.stopped && (!this.ws || this.ws.readyState !== WebSocket.OPEN)) {
        this.connect();
      }
    }, 5000);
  }

  connect() {
    if (this.stopped) return;
    try {
      if (this.ws) { this.ws.onclose = null; this.ws.close(); }
      this.ws = new WebSocket(`${WS}/ws/alerts`);
      this.ws.onopen    = () => { this.onStatus('connected'); this.delay = 2000; };
      this.ws.onmessage = e  => {
        try {
          const m = JSON.parse(e.data);
          if (m.type === 'alert') this.onAlert(m.data);
        } catch {}
      };
      this.ws.onclose = () => {
        this.onStatus('disconnected');
        if (!this.stopped) {
          setTimeout(() => this.connect(), this.delay);
          this.delay = Math.min(this.delay * 1.5, 10000);
        }
      };
      this.ws.onerror = () => this.ws.close();
    } catch { this.onStatus('error'); }
  }

  close() { this.stopped = true; this.ws && this.ws.close(); }
}

/* ── Sidebar counter (localStorage-based, persists across pages) ── */
const sidebarCounters = {
  _pollInterval: null,

  init() {
    if (localStorage.getItem('anomaly_baseline') === null) {
      api.dashboard().then(s => {
        localStorage.setItem('anomaly_baseline', String(s.total_alerts_all_time || 0));
      }).catch(() => {});
    }
    this._render();
    this._startPolling();
    // Reset when user clicks Alerts link
    document.getElementById('sb-badge-alerts')?.closest('a')
      ?.addEventListener('click', () => this.reset());
  },

  _startPolling() {
    this._pollInterval = setInterval(() => {
      api.dashboard().then(s => {
        const baseline = parseInt(localStorage.getItem('anomaly_baseline') || '0');
        const current  = s.total_alerts_all_time || 0;
        const newCount = Math.max(0, current - baseline);
        localStorage.setItem('anomaly_new_count', String(newCount));
        this._render();
      }).catch(() => {});
    }, 4000);
  },

  reset() {
    api.dashboard().then(s => {
      localStorage.setItem('anomaly_baseline', String(s.total_alerts_all_time || 0));
      localStorage.removeItem('anomaly_new_count');
      this._render();
    }).catch(() => {
      localStorage.removeItem('anomaly_new_count');
      this._render();
    });
  },

  _render() {
    const count = parseInt(localStorage.getItem('anomaly_new_count') || '0');
    // Dashboard badge — always hidden
    const dash = document.getElementById('sb-badge-dash');
    if (dash) dash.style.display = 'none';
    // Alerts badge
    const alerts = document.getElementById('sb-badge-alerts');
    if (!alerts) return;
    if (count > 0) {
      alerts.textContent = count > 99 ? '99+' : count;
      alerts.style.display = 'flex';
      alerts.classList.remove('pulse');
      void alerts.offsetWidth;
      alerts.classList.add('pulse');
    } else {
      alerts.style.display = 'none';
    }
  }
};

/* ── Toast notifications ── */
const toast = {
  _c: null,
  _init() {
    if (!this._c) {
      this._c = document.createElement('div');
      this._c.className = 'toast-container';
      document.body.appendChild(this._c);
    }
  },
  show(msg, type='info', ms=3500) {
    this._init();
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = msg;
    this._c.appendChild(t);
    setTimeout(() => {
      t.style.transition = 'opacity .3s';
      t.style.opacity = '0';
      setTimeout(() => t.remove(), 300);
    }, ms);
  },
  success: m => toast.show(m, 'success'),
  error:   m => toast.show(m, 'error'),
  info:    m => toast.show(m, 'info'),
  warn:    m => toast.show(m, 'warn'),
};

/* ── Shared helpers ── */
const fmt = {
  $: v => '$' + parseFloat(v).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}),
  time: iso => {
    const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
    return d.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false});
  },
  dt: iso => {
    const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
    return d.toLocaleString('en-US', {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit', hour12:false});
  },
  scoreColor: s => s >= 70 ? 'var(--red)' : s >= 40 ? 'var(--yellow)' : 'var(--green)',
};

function levelBadge(l)  { return `<span class="badge bg-${l}">${l}</span>`; }
function statusBadge(s) { return `<span class="badge bg-${s}">${s.replace('_',' ')}</span>`; }
function set(id, v) { const e = document.getElementById(id); if (e) e.textContent = v; }

function initClock(id='clock') {
  const el = document.getElementById(id); if (!el) return;
  const tick = () => el.textContent = new Date().toLocaleTimeString('en-US', {hour12:false, hour:'2-digit', minute:'2-digit', second:'2-digit'});
  tick(); setInterval(tick, 1000);
}

function setWsStatus(status) {
  const dot = document.getElementById('live-dot');
  const txt = document.getElementById('live-txt');
  if (dot) dot.style.background = status === 'connected' ? 'var(--green)' : 'var(--yellow)';
  if (txt) txt.textContent = status === 'connected' ? 'LIVE' : 'RECONNECTING';
}

/* ── Screen shake + flash banner on high-risk alert ── */
function triggerShakeAndFlash(alert) {
  // document.querySelector('.main')?.scrollTo({ top: 0, behavior: 'smooth' });
  if (alert.level === 'high') {
    const layout = document.querySelector('.layout');
    if (layout) {
      layout.classList.remove('shake');
      void layout.offsetWidth;
      layout.classList.add('shake');
      setTimeout(() => layout.classList.remove('shake'), 700);
    }
    const existing = document.querySelector('.alert-flash');
    if (existing) existing.remove();
    const banner = document.createElement('div');
    banner.className = 'alert-flash';
    banner.innerHTML = `
      <div class="flash-dot"></div>
      ⚠ HIGH RISK — ${alert.user_id} — ${fmt.$(alert.amount)} — ${alert.reason}
      <span style="margin-left:auto;cursor:pointer;opacity:.7" onclick="this.parentElement.remove()">✕</span>`;
    document.body.prepend(banner);
    setTimeout(() => { if (banner.parentElement) banner.remove(); }, 5000);
  } else {
    toast.warn(`New ${alert.level.toUpperCase()} alert: ${alert.id}`);
  }
}
