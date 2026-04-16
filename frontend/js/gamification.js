/* Gamification page */
const ANALYST = 'Sr. Analyst';
const API_G   = `${BASE}/api/gamification`;

let _profile = null;

async function loadProfile() {
  try {
    const data = await fetch(`${API_G}/profile/${encodeURIComponent(ANALYST)}`).then(r=>r.json());
    _profile = data;
    renderProfile(data.profile);
    renderBadges(data.badges);
    renderChallenges(data.challenges);
    renderLeaderboard(data.leaderboard);
    renderXPLog(data.xp_log);
  } catch(e) { console.error('[Gamification]', e); }
}

function renderProfile(p) {
  set('g-name',    p.display_name);
  set('g-title',   p.title);
  set('g-level',   p.level);
  set('g-xp',      p.xp.toLocaleString());
  set('g-detections', p.total_detections);
  set('g-cases',   p.total_cases);
  set('g-fp',      p.total_fp);
  set('g-prevented', '$' + (p.fraud_prevented / 1000).toFixed(1) + 'K');
  set('g-streak',  p.streak_days + ' days');

  // XP progress bar
  const bar = document.getElementById('xp-bar');
  if (bar) { bar.style.width = p.xp_progress_pct + '%'; }
  set('xp-pct', p.xp_progress_pct + '%');
  if (p.next_level_xp) {
    set('next-xp', `${p.xp.toLocaleString()} / ${p.next_level_xp.toLocaleString()} XP`);
  }

  // Level ring color
  const ring = document.getElementById('level-ring');
  if (ring) {
    const colors = ['','var(--txt3)','var(--green)','var(--cyan)','var(--yellow)','var(--red)','var(--purple)','#ff6b35','#e91e8c','#00bcd4','#ffd700'];
    ring.style.borderColor = colors[Math.min(p.level, colors.length-1)];
    ring.style.boxShadow   = `0 0 20px ${colors[Math.min(p.level, colors.length-1)]}40`;
  }
}

function renderBadges(badges) {
  const locked   = document.getElementById('badges-locked');
  const unlocked = document.getElementById('badges-unlocked');
  if (!locked || !unlocked) return;

  const u = badges.filter(b => b.unlocked);
  const l = badges.filter(b => !b.unlocked);

  unlocked.innerHTML = u.length ? u.map(b => `
    <div class="badge-card unlocked" title="${b.description}">
      <div class="badge-icon">${b.icon}</div>
      <div class="badge-name">${b.name}</div>
      <div class="badge-xp">+${b.xp} XP</div>
      <div class="badge-date">${b.unlocked_at ? new Date(b.unlocked_at+'Z').toLocaleDateString() : ''}</div>
    </div>`) .join('') :
    '<div style="color:var(--txt3);font-family:var(--mono);font-size:10px;padding:10px">No badges yet — start investigating!</div>';

  locked.innerHTML = l.map(b => `
    <div class="badge-card locked" title="${b.description}">
      <div class="badge-icon" style="filter:grayscale(1);opacity:.4">${b.icon}</div>
      <div class="badge-name" style="color:var(--txt3)">${b.name}</div>
      <div class="badge-xp" style="color:var(--txt3)">+${b.xp} XP</div>
      <div class="badge-desc">${b.description}</div>
    </div>`).join('');
}

function renderChallenges(challenges) {
  const el = document.getElementById('challenges-list'); if (!el) return;
  el.innerHTML = challenges.map(c => {
    const pct   = Math.round(c.current / c.target * 100);
    const color = c.completed ? 'var(--green)' : 'var(--cyan)';
    const expires = new Date(c.expires+'Z');
    const hoursLeft = Math.max(0, Math.round((expires - Date.now()) / 3600000));
    return `
    <div class="challenge-card ${c.completed ? 'done' : ''}">
      <div class="challenge-header">
        <span class="challenge-icon">${c.icon}</span>
        <span class="challenge-title">${c.title}</span>
        <span class="challenge-xp">+${c.xp} XP</span>
        ${c.completed ? '<span class="badge bg-low" style="margin-left:6px">DONE</span>' : ''}
      </div>
      <div class="challenge-desc">${c.desc}</div>
      <div class="challenge-progress">
        <div class="challenge-bar-track">
          <div class="challenge-bar-fill" style="width:${pct}%;background:${color}"></div>
        </div>
        <span class="challenge-count">${c.current}/${c.target}</span>
      </div>
      <div class="challenge-expire">Resets in ${hoursLeft}h</div>
    </div>`;
  }).join('');
}

function renderLeaderboard(lb) {
  const el = document.getElementById('leaderboard-list'); if (!el) return;
  el.innerHTML = lb.map(e => {
    const isMe = e.name === ANALYST;
    const medals = ['🥇','🥈','🥉'];
    const medal  = e.rank <= 3 ? medals[e.rank-1] : `#${e.rank}`;
    return `
    <div class="lb-row ${isMe ? 'lb-me' : ''}">
      <span class="lb-rank">${medal}</span>
      <div class="lb-name-wrap">
        <span class="lb-name">${e.display}${isMe ? ' <span style="color:var(--cyan);font-size:9px">(you)</span>' : ''}</span>
        <span class="lb-level">Lv.${e.level}</span>
      </div>
      <div class="lb-stats">
        <span class="lb-stat" title="Detection Rate">🎯 ${e.dr}%</span>
        <span class="lb-stat" title="FP Rate">⚠ ${e.fpr}%</span>
        <span class="lb-stat" title="Cases">📂 ${e.cases}</span>
      </div>
      <span class="lb-xp">${e.xp.toLocaleString()} XP</span>
    </div>`;
  }).join('');
}

function renderXPLog(log) {
  const el = document.getElementById('xp-log'); if (!el) return;
  if (!log.length) {
    el.innerHTML = '<div style="color:var(--txt3);font-family:var(--mono);font-size:10px;padding:16px">No XP events yet</div>';
    return;
  }
  el.innerHTML = log.map(e => {
    const pos   = e.delta >= 0;
    const color = pos ? 'var(--green)' : 'var(--red)';
    return `
    <div style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid var(--border)">
      <span style="font-family:var(--mono);font-size:12px;font-weight:700;color:${color};min-width:52px;text-align:right">
        ${pos ? '+' : ''}${e.delta} XP
      </span>
      <span style="font-size:11px;color:var(--txt2);flex:1">${e.desc}</span>
      <span style="font-family:var(--mono);font-size:9px;color:var(--txt3)">${fmt.time(e.at)}</span>
    </div>`;
  }).join('');
}

// Award XP when analyst confirms feedback
async function awardForAction(eventType, description, amount = 0) {
  try {
    const r = await fetch(
      `${API_G}/award?analyst_name=${encodeURIComponent(ANALYST)}&event_type=${eventType}&description=${encodeURIComponent(description)}&amount=${amount}`,
      { method: 'POST' }
    ).then(r => r.json());

    if (r.xp_delta !== 0) {
      const color = r.xp_delta > 0 ? 'success' : 'error';
      toast[color](`${r.xp_delta > 0 ? '+' : ''}${r.xp_delta} XP — ${description}`);
    }
    if (r.level_up) {
      setTimeout(() => toast.success(`🎉 LEVEL UP! You are now Level ${r.new_level}: ${r.title}`), 800);
    }
    if (r.achievements_unlocked?.length) {
      r.achievements_unlocked.forEach(a => {
        setTimeout(() => toast.success(`🏆 Achievement Unlocked: ${a.icon} ${a.name} (+${a.xp} XP)`), 1200);
      });
    }
    // Refresh gamification page if open
    if (window.location.pathname.includes('gamification')) {
      setTimeout(loadProfile, 500);
    }
  } catch {}
}

// Expose globally so other pages can call it
window.awardForAction = awardForAction;

document.addEventListener('DOMContentLoaded', async () => {
  initClock();
  sidebarCounters.init();
  new AlertStream(alert => { sidebarCounters.onNewAlert(alert); }, () => {});
  await loadProfile();
  setInterval(loadProfile, 15000);
});

// Load success criteria on gamification page
async function loadCriteria() {
  try {
    const p = await api.performance();
    const drEl = document.getElementById('crit-dr-val');
    const fpEl = document.getElementById('crit-fp-val');
    const drCard = document.getElementById('crit-dr');
    const fpCard = document.getElementById('crit-fp');

    if (drEl && p.total_predictions > 0) {
      const dr = (p.detection_rate * 100).toFixed(1);
      drEl.textContent = dr + '%';
      drEl.style.color = p.detection_rate > 0.85 ? 'var(--green)' : 'var(--red)';
      if (drCard) drCard.style.borderColor = p.detection_rate > 0.85 ? 'var(--green)' : 'var(--red)';
    } else if (drEl) { drEl.textContent = 'N/A'; }

    if (fpEl && p.total_predictions > 0) {
      const fpr = (p.fp_rate * 100).toFixed(1);
      fpEl.textContent = fpr + '%';
      fpEl.style.color = p.fp_rate < 0.05 ? 'var(--green)' : 'var(--red)';
      if (fpCard) fpCard.style.borderColor = p.fp_rate < 0.05 ? 'var(--green)' : 'var(--red)';
    } else if (fpEl) { fpEl.textContent = 'N/A'; }
  } catch {}
}

// Override DOMContentLoaded to also load criteria
document.addEventListener('DOMContentLoaded', () => {
  if (window.location.pathname.includes('gamification')) {
    loadCriteria();
  }
});
