// ─── STATE ────────────────────────────────────────────────────
let currentUser  = null;
let mapData      = [];
let liveMode     = false;
let liveInterval = null;
let mapRefresh   = null;
let leafletMap   = null;
let leafletMarkers = [];
let labDebounce  = null;
let lastUpdatedAt = null;

// Shift Tracker state
let shiftActive   = false;
let shiftStart    = null;
let shiftTimer    = null;
let earningsLog   = [];   // [{hour, amount, note, ts}]
let shiftAiTicker = null;

const DAYS = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
const inr  = n => "₹" + Number(n).toLocaleString("en-IN");
const $    = id => document.getElementById(id);

function _injectUserParams(path) {
  if (!currentUser) return path;
  const sep = path.includes("?") ? "&" : "?";
  const p = new URLSearchParams();
  if (currentUser.city)      p.set("city",      currentUser.city);
  if (currentUser.income)    p.set("income",    currentUser.income);
  if (currentUser.work_type) p.set("work_type", currentUser.work_type);
  if (currentUser.risk_score !== undefined) p.set("risk_score", currentUser.risk_score);
  if (currentUser.name)      p.set("name",      currentUser.name);
  return path + sep + p.toString();
}

async function api(path) {
  const r = await fetch(_injectUserParams(path));
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
async function post(path, body) {
  const enriched = currentUser ? {
    city: currentUser.city, income: currentUser.income,
    work_type: currentUser.work_type, risk_score: currentUser.risk_score,
    name: currentUser.name, ...body,
  } : body;
  const r = await fetch(path, {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify(enriched),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
function showScreen(name) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  $(name + "-screen").classList.add("active");
}

// ─── STATUS BAR ───────────────────────────────────────────────
function showStatusBar() {
  $("status-bar").style.display = "flex";
  updateStatusTime();
}
function updateStatusTime() {
  lastUpdatedAt = new Date();
  $("sys-last-updated").textContent = "just now";
}
function startStatusClock() {
  setInterval(() => {
    if (!lastUpdatedAt) return;
    const s = Math.round((Date.now() - lastUpdatedAt.getTime()) / 1000);
    $("sys-last-updated").textContent = s < 60 ? `${s}s ago` : `${Math.round(s/60)}m ago`;
  }, 1000);
}
function setDataSources(w, a, l) {
  const badge = (id, ok, lbl) => {
    const el = $(id); if (!el) return;
    el.classList.toggle("inactive", !ok);
    el.textContent = ok ? `${lbl} ✓` : `${lbl} ✗`;
  };
  badge("src-weather", w, "Weather");
  badge("src-aqi", a, "AQI");
  badge("src-location", l, "Location");
}

// ─── REGISTRATION ─────────────────────────────────────────────
$("register-btn").addEventListener("click", async () => {
  const name      = $("reg-name").value.trim();
  const city      = $("reg-city").value.trim();
  const income    = parseInt($("reg-income").value) || 20000;
  const work_type = $("reg-type").value;
  if (!name || !city) { $("register-error").textContent = "Name and city are required."; return; }
  $("register-error").textContent = "";
  $("reg-btn-text").textContent   = "ACTIVATING...";
  $("register-btn").disabled = true;
  try {
    const data = await post("/register", { name, city, income, work_type });
    currentUser = data;
    localStorage.setItem("nexashift_user", JSON.stringify(data));
    initApp();
  } catch (e) {
    $("register-error").textContent = "Registration failed. Please try again.";
  } finally {
    $("reg-btn-text").textContent = "ACTIVATE PROTECTION →";
    $("register-btn").disabled = false;
  }
});

// ─── LOGOUT ───────────────────────────────────────────────────
$("logout-btn").addEventListener("click", () => {
  stopLiveMode();
  clearInterval(mapRefresh);
  clearInterval(shiftTimer);
  clearInterval(shiftAiTicker);
  localStorage.removeItem("nexashift_user");
  currentUser = null;
  earningsLog = [];
  shiftActive = false;
  shiftStart  = null;
  $("status-bar").style.display = "none";
  if (leafletMap) { leafletMap.remove(); leafletMap = null; leafletMarkers = []; }
  showScreen("register");
});

// ─── ROLE SELECTION ───────────────────────────────────────────
function selectRole(role) {
  document.querySelectorAll(".role-btn").forEach(b => b.classList.remove("active"));
  $("role-" + role).classList.add("active");
  if (role === "admin") {
    $("worker-form-section").style.display = "none";
    $("admin-redirect-section").style.display = "block";
  } else {
    $("worker-form-section").style.display = "block";
    $("admin-redirect-section").style.display = "none";
  }
}

// ─── TABS ─────────────────────────────────────────────────────
function switchTab(tabName) {
  document.querySelectorAll(".nav-tab").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
  const btn = document.querySelector(`.nav-tab[data-tab="${tabName}"]`);
  if (btn) btn.classList.add("active");
  const tabEl = $("tab-" + tabName);
  if (tabEl) tabEl.classList.add("active");
  if (tabName === "tracker")   initTrackerTab();
  if (tabName === "autopilot") initAutopilot();
  if (tabName === "shield")    loadIncomeShield();
  if (tabName === "lab")       initScenarioLab();
  if (tabName === "map")       loadMap();
  if (tabName === "claims")    loadClaims();
  if (tabName === "insights")  loadInsights();
}

document.querySelectorAll(".nav-tab").forEach(btn => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

// ─── INIT APP ─────────────────────────────────────────────────
function initApp() {
  showScreen("app");
  showStatusBar();
  startStatusClock();
  $("nav-username").textContent = currentUser.name;
  $("nav-avatar").textContent   = currentUser.name.charAt(0).toUpperCase();
  loadDashboard();
  setupLiveMode();
  setupGeoLocation();
  setupMapToggle();
  initDemoMode();
  // Handle cross-page tab navigation from admin
  const gotoTab = localStorage.getItem("nexashift_goto_tab");
  if (gotoTab) {
    localStorage.removeItem("nexashift_goto_tab");
    setTimeout(() => switchTab(gotoTab), 200);
  }
}

// ─── WEATHER ──────────────────────────────────────────────────
function updateWeatherStrip(weather, aqi) {
  if (!weather) return;
  $("w-temp").textContent     = (weather.temp || "—") + "°C";
  $("w-rain").textContent     = (weather.rainfall || 0) + " mm/hr";
  $("w-humidity").textContent = (weather.humidity || "—") + "%";
  $("w-aqi").textContent      = "AQI " + (aqi || "—");
  $("w-desc").textContent     = weather.description || "—";
  $("w-source").textContent   = weather.source === "openweathermap" ? "● Live OWM" : "● Simulated";
  setDataSources(true, true, true);
  updateStatusTime();
}

// ─── DASHBOARD ────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const [summary, triggers, plan] = await Promise.all([
      api(`/dashboard/summary?user_id=${currentUser.user_id}`),
      api("/triggers"),
      api(`/daily-plan/${currentUser.user_id}`),
    ]);
    $("stat-income").textContent   = inr(summary.monthly_income);
    $("stat-risk").textContent     = summary.risk_score + "/100";
    $("stat-coverage").textContent = inr(summary.coverage);
    $("stat-premium").textContent  = inr(summary.premium);
    $("dash-city-label").textContent = `${summary.city} · ${(summary.work_type||"").replace("_"," ")} · Risk ${summary.risk_score}/100`;

    const risk = summary.risk_score;
    const bar  = $("risk-bar");
    bar.style.width      = risk + "%";
    bar.style.background = risk > 70 ? "var(--danger)" : risk > 45 ? "var(--warning)" : "var(--success)";

    const rChip = $("dash-risk-chip");
    const rLabel = risk > 70 ? "HIGH RISK" : risk > 45 ? "MEDIUM RISK" : "LOW RISK";
    const rClass = risk > 70 ? "rc-high" : risk > 45 ? "rc-med" : "rc-low";
    rChip.innerHTML = `<span class="risk-chip ${rClass}">${rLabel}</span>`;

    if (summary.weather) updateWeatherStrip(summary.weather, summary.aqi||100);
    renderTriggers(triggers);
    renderDailyPlan(plan);
    if (risk > 50) fetchAutoSwitch();
    else $("auto-switch-alert").style.display = "none";
    loadMLQuickCard();
  } catch (e) { console.error("Dashboard:", e); }
}

async function fetchAutoSwitch() {
  try {
    const h    = new Date().getHours();
    const data = await api(`/scenario-lab?user_id=${currentUser.user_id}&rain=5&aqi=150&hour=${h}`);
    if (data.auto_switch) {
      const sw = data.auto_switch;
      $("auto-switch-body").innerHTML = `
        <div class="switch-suggestion">
          <div class="switch-info">
            <div class="switch-title">Switch to: ${sw.label}</div>
            <div class="switch-reason">${sw.reason}</div>
          </div>
          <div class="switch-gain">+${inr(sw.expected_gain)} expected</div>
        </div>`;
      $("auto-switch-alert").style.display = "block";
    }
  } catch (_) {}
}

async function loadMLQuickCard() {
  if (!currentUser) return;
  const el = $("ml-quick-content");
  if (!el) return;
  try {
    const h = new Date().getHours();
    const data = await api(`/ml/predict-risk?user_id=${currentUser.user_id}&hour=${h}`);
    const contribs = data.feature_contributions || {};
    const entries = Object.entries(contribs);
    const maxC = Math.max(...entries.map(([,v])=>v), 1);
    el.innerHTML = `
      <div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:.9rem">
        <div><div style="font-size:1.7rem;font-weight:800;color:${data.risk_score>70?"var(--danger)":data.risk_score>45?"var(--warning)":"var(--success)"}">${data.risk_score}<span style="font-size:.9rem;font-weight:400;color:var(--text-muted)">/100</span></div><div style="font-size:.65rem;text-transform:uppercase;letter-spacing:.07em;color:var(--text-muted)">Risk Score</div></div>
        <div><div style="font-size:1.7rem;font-weight:800;color:var(--accent)">${data.confidence_pct}%</div><div style="font-size:.65rem;text-transform:uppercase;letter-spacing:.07em;color:var(--text-muted)">Confidence</div></div>
        <div style="flex:1;min-width:180px">${entries.map(([name,val])=>`
          <div style="margin-bottom:.35rem">
            <div style="display:flex;justify-content:space-between;font-size:.72rem;margin-bottom:.18rem"><span style="color:var(--text-muted)">${name}</span><span style="font-weight:600">${val}</span></div>
            <div style="height:4px;background:var(--bg-card2);border-radius:99px"><div style="height:100%;width:${Math.round(val/maxC*100)}%;background:var(--accent);border-radius:99px;transition:width .5s"></div></div>
          </div>`).join("")}
        </div>
      </div>
      <div style="font-size:.72rem;color:var(--text-muted)">Model: ${data.model_version} · Worker: ${data.worker_type} · City: ${data.city}</div>`;
  } catch (e) {
    el.innerHTML = '<div style="color:var(--text-muted);font-size:.82rem">ML model loading...</div>';
  }
}

function renderTriggers(data) {
  const el       = $("triggers-list");
  const triggers = data.active_triggers || [];
  const dot      = $("trigger-dot");
  if (!triggers.length) {
    el.innerHTML = '<div class="loading">✅ No active risk triggers right now.</div>';
    if (dot) { dot.className = "refresh-dot dot-ok"; }
    return;
  }
  if (dot) dot.className = "refresh-dot dot-alert";
  el.innerHTML = triggers.map(t => `
    <div class="trigger-item">
      <span class="trigger-badge badge-${t.severity}">${t.severity.toUpperCase()}</span>
      <div>
        <div class="trigger-text">${t.description}</div>
        <div class="trigger-cities">📍 ${t.cities.join(", ")}</div>
        ${t.auto_payout && t.payout_amount > 0
          ? `<div class="trigger-payout">🛡 Auto-payout: ${inr(t.payout_amount)} triggered</div>` : ""}
      </div>
    </div>`).join("");
  const n = data.auto_claims_processed || 0;
  if (n > 0) showAutoPayout(`${n} auto-claim(s) processed — zero human action needed.`);
}

function showAutoPayout(msg) {
  $("auto-payout-msg").textContent = msg;
  $("auto-payout-alert").style.display = "flex";
  setTimeout(() => { $("auto-payout-alert").style.display = "none"; }, 14000);
}

function renderDailyPlan(plan) {
  const rows = [
    ["Weather",  plan.weather],
    ["Best Hrs", (plan.best_hours||[]).join(" / ")],
    ["Avoid",    (plan.avoid_hours||[]).join(", ") || "None"],
    ["Expected", inr(plan.expected_earnings) + " today"],
    ["AQI",      plan.aqi ? `AQI ${plan.aqi}` : "—"],
    ["Tip",      plan.recommendation],
  ];
  $("daily-plan-content").innerHTML = rows.map(([k,v]) => `
    <div class="plan-row"><span class="plan-label">${k}</span><span>${v}</span></div>`).join("");
}

// ─── LIVE MODE ────────────────────────────────────────────────
function setupLiveMode() {
  const toggle = $("live-toggle");
  toggle.addEventListener("change", () => toggle.checked ? startLiveMode() : stopLiveMode());
}
function startLiveMode() {
  liveMode = true;
  $("live-badge").style.display = "inline-block";
  $("live-decision-display").style.display = "flex";
  $("live-hint").textContent = "Analyzing every 10 seconds...";
  fetchLiveDecision();
  liveInterval = setInterval(fetchLiveDecision, 10000);
}
function stopLiveMode() {
  liveMode = false;
  clearInterval(liveInterval); liveInterval = null;
  $("live-badge").style.display = "none";
  $("live-decision-display").style.display = "none";
  $("live-hint").textContent = "AI decisions every 10s";
}
async function fetchLiveDecision() {
  if (!currentUser) return;
  try {
    const data  = await api(`/live-decision/${currentUser.user_id}`);
    const badge = $("live-rec-badge");
    badge.textContent = data.recommendation;
    badge.className   = "live-rec rec-" + (data.color || "success");
    $("live-earning").textContent =
      `Next hour: ${inr(data.expected_earnings_next_hour)}` + (data.surge_active ? " 🔥 SURGE" : "");
    $("live-reason").textContent = (data.reasons||[]).join(" · ") || data.advice;
    if (data.weather) updateWeatherStrip(data.weather, data.aqi||100);
    if (data.auto_trigger_fired && data.payout_triggered > 0)
      showAutoPayout(`Auto-trigger fired! Payout of ${inr(data.payout_triggered)} initiated.`);
    updateStatusTime();
    if (shiftActive) updateShiftAiTips(data);
  } catch (e) { console.error("Live decision:", e); }
}

// ─── GEOLOCATION ──────────────────────────────────────────────
function setupGeoLocation() {
  $("geo-btn").addEventListener("click", () => {
    if (!navigator.geolocation) { $("geo-btn").textContent = "Not supported"; return; }
    $("geo-btn").textContent = "📍 Locating...";
    $("geo-btn").disabled = true;
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const data = await post("/location-update", {
            user_id: currentUser?.user_id, lat: pos.coords.latitude, lng: pos.coords.longitude,
          });
          $("geo-btn").textContent = `📍 ${data.nearest_city}`;
          if (data.weather) updateWeatherStrip(data.weather, data.aqi||100);
          if (currentUser && data.nearest_city !== currentUser.city) currentUser.city = data.nearest_city;
          setDataSources(true, true, true);
        } catch (_) { $("geo-btn").textContent = "📍 Error"; }
        $("geo-btn").disabled = false;
      },
      () => { $("geo-btn").textContent = "📍 Denied"; $("geo-btn").disabled = false; }
    );
  });
}

// ─── SHIFT TRACKER ────────────────────────────────────────────
function initTrackerTab() {
  const now = new Date();
  $("tracker-date").textContent = now.toLocaleDateString("en-IN", {
    weekday:"long", day:"numeric", month:"long",
  });
  updateDailyTarget();
  renderHourlyLog();
  if (shiftActive) {
    tickTimer();
    updateShiftStatus("active");
  }
}

function updateDailyTarget() {
  if (!currentUser) return;
  const monthly = currentUser.income || 20000;
  const daily   = Math.round(monthly / 26);
  const earned  = earningsLog.reduce((a, e) => a + e.amount, 0);
  const remain  = Math.max(0, daily - earned);
  const pct     = Math.min(100, Math.round((earned / daily) * 100));
  const hours   = shiftStart
    ? ((Date.now() - shiftStart) / 3600000)
    : earningsLog.length;
  const rate    = hours > 0 ? Math.round(earned / hours) : "—";

  $("daily-target-val").textContent = inr(daily);
  $("earned-today").textContent     = inr(earned);
  $("remaining-today").textContent  = inr(remain);
  $("hourly-rate").textContent      = typeof rate === "number" ? inr(rate) + "/hr" : "—";
  $("ring-pct").textContent         = pct + "%";

  const circumference = 314;
  const offset = circumference - (pct / 100) * circumference;
  const fill = $("ring-fill");
  fill.style.strokeDashoffset = offset;
  fill.style.stroke = pct >= 100 ? "var(--success)" : pct >= 60 ? "var(--warning)" : "var(--accent)";
}

// Start Shift
$("shift-start-btn").addEventListener("click", () => {
  shiftActive = true;
  shiftStart  = Date.now();
  $("shift-start-btn").style.display = "none";
  $("shift-end-btn").style.display   = "inline-flex";
  $("timer-label").textContent = "SHIFT IN PROGRESS";
  $("timer-display").classList.add("running");
  $("tracker-dot-nav").style.display = "inline-block";
  updateShiftStatus("active");
  shiftTimer = setInterval(tickTimer, 1000);
  $("ai-tip-conditions").style.display = "block";
  fetchShiftAiTips();
  shiftAiTicker = setInterval(fetchShiftAiTips, 30000);
});

// End Shift
$("shift-end-btn").addEventListener("click", () => {
  shiftActive = false;
  clearInterval(shiftTimer);
  clearInterval(shiftAiTicker);
  $("shift-start-btn").style.display = "inline-flex";
  $("shift-end-btn").style.display   = "none";
  $("timer-label").textContent = "SHIFT ENDED";
  $("timer-display").classList.remove("running");
  $("tracker-dot-nav").style.display = "none";
  showEodSummary();
});

function tickTimer() {
  if (!shiftStart) return;
  const elapsed = Math.floor((Date.now() - shiftStart) / 1000);
  const h = String(Math.floor(elapsed / 3600)).padStart(2,"0");
  const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2,"0");
  const s = String(elapsed % 60).padStart(2,"0");
  $("timer-display").textContent = `${h}:${m}:${s}`;
  updateDailyTarget();
}

function updateShiftStatus(state) {
  if (state === "active") {
    $("shift-status").textContent = "🛡 Protection active · AI monitoring conditions · Auto-payout enabled";
    $("shift-status").style.color = "var(--success)";
  }
}

async function fetchShiftAiTips() {
  if (!currentUser) return;
  try {
    const h    = new Date().getHours();
    const data = await api(`/scenario-lab?user_id=${currentUser.user_id}&rain=0&aqi=100&hour=${h}`);
    updateShiftAiTips(data);
  } catch (_) {}
}

function updateShiftAiTips(data) {
  const tip = $("ai-tip-main");
  const rec = data.recommendation || "Conditions look stable. Keep going!";
  const lvl = data.rec_level || "safe";
  const col = lvl === "critical" ? "var(--danger)" : lvl === "warning" ? "var(--warning)" : lvl === "moderate" ? "#f59e0b" : "var(--success)";
  tip.querySelector(".ai-tip-text").textContent = rec;
  tip.querySelector(".ai-tip-icon").textContent = lvl === "critical" ? "🚨" : lvl === "warning" ? "⚠️" : "💡";

  if ($("tip-rain"))   $("tip-rain").textContent   = (data.input_rain||0) + " mm/hr";
  if ($("tip-aqi"))    $("tip-aqi").textContent    = (data.input_aqi||100) + " (" + aqiCat(data.input_aqi||100) + ")";
  if ($("tip-demand")) $("tip-demand").textContent = data.demand_score ? data.demand_score + "/100" : "—";
  if ($("tip-risk"))   $("tip-risk").textContent   = (data.risk||0) + "/100";
  if ($("tip-risk"))   $("tip-risk").style.color   = col;
}

// Log Entry
$("log-entry-btn").addEventListener("click", () => {
  const hour   = parseInt($("log-hour").value);
  const amount = parseInt($("log-amount").value);
  const note   = $("log-note").value.trim();
  if (isNaN(hour) || hour < 0 || hour > 23) { alert("Enter a valid hour (0–23)."); return; }
  if (isNaN(amount) || amount <= 0) { alert("Enter a valid positive amount."); return; }
  earningsLog.push({ hour, amount, note, ts: Date.now() });
  $("log-hour").value   = "";
  $("log-amount").value = "";
  $("log-note").value   = "";
  const s = $("log-success");
  s.style.display  = "block";
  s.textContent    = `✅ Added ₹${amount.toLocaleString("en-IN")} for ${fmtHour(hour)}`;
  setTimeout(() => { s.style.display = "none"; }, 2500);
  renderHourlyLog();
  updateDailyTarget();
});

function renderHourlyLog() {
  const el    = $("hourly-log-content");
  const total = earningsLog.reduce((a, e) => a + e.amount, 0);
  $("log-total-chip").textContent = "Total: " + inr(total);
  if (!earningsLog.length) {
    el.innerHTML = `<div class="log-empty"><div class="log-empty-icon">📋</div><div>No entries yet — log your first hour above</div></div>`;
    return;
  }
  const sorted = [...earningsLog].sort((a,b) => a.hour - b.hour);
  el.innerHTML = `<table class="log-table">
    <thead><tr><th>Time</th><th>Earnings</th><th>Note</th><th></th></tr></thead>
    <tbody>
    ${sorted.map((e,i) => `<tr>
      <td>${fmtHour(e.hour)}</td>
      <td class="log-amount-cell">${inr(e.amount)}</td>
      <td style="color:var(--text-muted);font-size:0.78rem">${e.note || "—"}</td>
      <td><button class="log-del-btn" data-idx="${earningsLog.indexOf(e)}" title="Remove">✕</button></td>
    </tr>`).join("")}
    </tbody>
  </table>`;
  el.querySelectorAll(".log-del-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      earningsLog.splice(parseInt(btn.dataset.idx), 1);
      renderHourlyLog(); updateDailyTarget();
    });
  });
}

function showEodSummary() {
  const card = $("eod-summary-card");
  card.style.display = "block";
  const monthly = currentUser?.income || 20000;
  const daily   = Math.round(monthly / 26);
  const total   = earningsLog.reduce((a, e) => a + e.amount, 0);
  const pct     = Math.round((total / daily) * 100);
  const elapsed = shiftStart ? ((Date.now() - shiftStart) / 3600000).toFixed(1) : 0;
  const rate    = elapsed > 0 ? Math.round(total / elapsed) : 0;
  const ai = total >= daily
    ? `Great work! You hit ${pct}% of your daily target. Consider taking the rest of the day off or earning extra buffer.`
    : `You earned ${pct}% of your daily target today. ${100-pct}% remains — try to catch up tomorrow by targeting peak hours (7-9 AM, 6-8 PM).`;

  $("eod-summary-content").innerHTML = `
    <div class="eod-grid">
      <div class="eod-box"><div class="eod-val" style="color:var(--success)">${inr(total)}</div><div class="eod-key">Total Earned</div></div>
      <div class="eod-box"><div class="eod-val">${elapsed}h</div><div class="eod-key">Hours Worked</div></div>
      <div class="eod-box"><div class="eod-val" style="color:var(--accent)">${inr(rate)}/hr</div><div class="eod-key">Avg Hourly Rate</div></div>
      <div class="eod-box"><div class="eod-val">${pct}%</div><div class="eod-key">Target Hit</div></div>
      <div class="eod-box"><div class="eod-val" style="color:${total>=daily?'var(--success)':'var(--warning)'}">
        ${total >= daily ? "✅ Done!" : inr(daily - total) + " left"}</div><div class="eod-key">Vs Daily Target</div>
      </div>
      <div class="eod-box"><div class="eod-val">${earningsLog.length}</div><div class="eod-key">Hours Logged</div></div>
    </div>
    <div class="eod-ai-tip">🤖 <strong>AI Summary:</strong> ${ai}</div>`;
}

// ─── INCOME SHIELD ────────────────────────────────────────────
async function loadIncomeShield() {
  if (!currentUser) return;
  try {
    const [summary, claims] = await Promise.all([
      api(`/dashboard/summary?user_id=${currentUser.user_id}`),
      api(`/claims/${currentUser.user_id}`),
    ]);
    const coverage = summary.coverage;
    const premium  = summary.premium;
    const risk     = summary.risk_score;
    const tier     = coverage > 60000 ? "Premium Shield" : coverage > 30000 ? "Standard Shield" : "Basic Shield";
    $("shield-tier").textContent         = tier;
    $("shield-coverage-val").textContent = inr(coverage);
    $("shield-premium").textContent      = inr(premium) + "/mo";
    $("shield-risk").textContent         = risk + "/100";
    $("shield-city").textContent         = summary.city;
    $("shield-work").textContent         = (summary.work_type||"").replace("_"," ");
    $("shield-days").textContent         = Math.floor(Math.random() * 45) + 10;
    const b = Math.round(coverage * 0.3);
    $("cov-rain").textContent     = inr(b);
    $("cov-aqi").textContent      = inr(Math.round(b * 0.75));
    $("cov-platform").textContent = inr(Math.round(b * 1.2));
    $("cov-accident").textContent = inr(Math.round(coverage * 0.8));
    if ($("claim-cmp-val")) $("claim-cmp-val").textContent = "Up to " + inr(coverage);
    renderProtectionEvents(claims);
  } catch (e) { console.error("Shield:", e); }
}

function renderProtectionEvents(claims) {
  const el = $("protection-events");
  if (!claims || !claims.length) {
    el.innerHTML = '<div class="loading">No events yet. Your shield is active and monitoring.</div>';
    $("events-count").textContent = "0 Events";
    return;
  }
  $("events-count").textContent = claims.length + " Events";
  const icons = {rain:"🌧",aqi:"😷",heat:"🌡",platform_outage:"📵",upi_down:"💳",accident:"🚑"};
  el.innerHTML = [...claims].reverse().map(c => {
    const icon = icons[c.claim_type] || "🛡";
    const dt   = c.timestamp
      ? new Date(c.timestamp).toLocaleDateString("en-IN",{month:"short",day:"numeric"}) : "—";
    return `<div class="event-item">
      <div class="event-icon">${icon}</div>
      <div>
        <div class="event-title">${(c.claim_type||"").replace("_"," ").replace(/\b\w/g,l=>l.toUpperCase())}</div>
        <div class="event-detail">${dt} · Claim #${c.claim_id} · ${c.status}</div>
      </div>
      <div class="event-amount">${c.status==="AUTO_APPROVED" ? "+"+inr(c.amount) : "Pending"}</div>
    </div>`;
  }).join("");
}

$("sos-btn").addEventListener("click", () => {
  document.querySelectorAll(".nav-tab").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
  document.querySelector('[data-tab="claims"]').classList.add("active");
  $("tab-claims").classList.add("active");
  $("claim-type").value   = "accident";
  $("claim-amount").value = 5000;
  $("claim-desc").value   = "Emergency SOS — accident/injury reported";
  $("claim-amount").scrollIntoView({behavior:"smooth",block:"center"});
  loadClaims();
});

// ─── SCENARIO LAB ─────────────────────────────────────────────
let labInitialized = false;
function initScenarioLab() {
  if (labInitialized) { fetchLabData(0, 100, 12); return; }
  labInitialized = true;
  const rain = $("rain-slider");
  const aqi  = $("aqi-slider");
  const hour = $("hour-slider");
  function onChange() {
    $("rain-val").textContent = rain.value + " mm/hr";
    $("aqi-val").textContent  = aqi.value + " (" + aqiCat(+aqi.value) + ")";
    $("hour-val").textContent = fmtHour(+hour.value);
    clearTimeout(labDebounce);
    labDebounce = setTimeout(() => fetchLabData(+rain.value, +aqi.value, +hour.value), 280);
  }
  rain.addEventListener("input", onChange);
  aqi.addEventListener("input",  onChange);
  hour.addEventListener("input", onChange);
  fetchLabData(0, 100, 12);
}
function aqiCat(v) {
  if (v < 51)  return "Good";
  if (v < 101) return "Moderate";
  if (v < 151) return "Sensitive";
  if (v < 201) return "Unhealthy";
  if (v < 301) return "Very Unhealthy";
  return "Hazardous";
}
function fmtHour(h) {
  if (h === 0)  return "12:00 AM";
  if (h < 12)   return `${h}:00 AM`;
  if (h === 12) return "12:00 PM";
  return `${h-12}:00 PM`;
}
async function fetchLabData(rain, aqi, hour) {
  const uid = currentUser?.user_id || "";
  try {
    const data = await api(`/scenario-lab?user_id=${uid}&rain=${rain}&aqi=${aqi}&hour=${hour}`);
    renderLabResults(data, hour);
  } catch (e) { console.error("Lab:", e); }
}
function renderLabResults(data, currentHour) {
  const risk = data.risk || 0;
  const fill = $("lab-risk-fill");
  fill.style.width      = risk + "%";
  fill.style.background = risk > 70 ? "var(--danger)" : risk > 40 ? "var(--warning)" : "var(--success)";
  $("lab-risk-val").textContent = risk + " / 100";
  $("lab-risk-val").style.color = risk > 70 ? "var(--danger)" : risk > 40 ? "var(--warning)" : "var(--success)";
  const level = data.rec_level || "safe";
  $("lab-rec-card").className = "card lab-rec-card rec-" + level;
  $("lab-rec-level").textContent = level.toUpperCase();
  $("lab-rec-text").textContent  = data.recommendation;
  const sw = $("lab-switch-card");
  if (data.auto_switch && risk > 40) {
    const s = data.auto_switch;
    $("lab-switch-body").innerHTML = `
      <div class="lab-switch-row">
        <span>Switch to: <strong>${s.label}</strong></span>
        <span class="lab-switch-gain">+${inr(s.expected_gain)} expected</span>
      </div>
      <div style="font-size:0.75rem;color:var(--text-muted);margin-top:0.3rem">${s.reason}</div>`;
    sw.style.display = "block";
  } else { sw.style.display = "none"; }
  const proj = data.projections || [];
  const maxV = Math.max(...proj.map(p => p.protected), 1);
  $("proj-chart").innerHTML = proj.map(p => {
    const bh = Math.round((p.income / maxV) * 96);
    const ph = Math.round((p.protected / maxV) * 96);
    return `<div class="proj-col">
      <div class="proj-bar prot-bar" style="height:${ph}px" title="${inr(p.protected)}"></div>
      <div class="proj-bar base-bar" style="height:${bh}px;margin-top:-${bh}px" title="${inr(p.income)}"></div>
    </div>`;
  }).join("");
  $("proj-labels").innerHTML = proj.map(p =>
    `<div class="proj-label ${p.hour===currentHour?"current":""}">${p.hour}</div>`).join("");
  $("cmp-without").textContent = inr(data.without_nexashift);
  $("cmp-with").textContent    = inr(data.with_nexashift);
  $("cmp-base").textContent    = inr(data.base_daily);
  $("cmp-loss").textContent    = "-" + inr(data.estimated_loss);
  $("cmp-payout").textContent  = "+" + inr(data.payout);
}

// ─── MAP ──────────────────────────────────────────────────────
async function loadMap() {
  if (!leafletMap) initLeafletMap();
  try {
    mapData = await api("/map-data");
    renderLeafletMarkers();
    clearInterval(mapRefresh);
    mapRefresh = setInterval(async () => {
      mapData = await api("/map-data");
      renderLeafletMarkers();
    }, 10000);
  } catch (e) { console.error("Map:", e); }
}
function initLeafletMap() {
  leafletMap = L.map("india-map", {center:[20.5937, 78.9629], zoom:5});
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution:"&copy; CARTO", subdomains:"abcd", maxZoom:19,
  }).addTo(leafletMap);
}
const riskColor = s => s > 70 ? "#f05252" : s > 45 ? "#f59e0b" : "#22c55e";
const riskLabel = s => s > 70 ? "HIGH" : s > 45 ? "MEDIUM" : "LOW";

function renderLeafletMarkers() {
  leafletMarkers.forEach(m => m.remove());
  leafletMarkers = [];
  mapData.forEach(city => {
    const col  = riskColor(city.risk_score);
    const icon = L.divIcon({
      className:"",
      html:`<div style="width:32px;height:32px;background:${col}18;border:2px solid ${col};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.6rem;font-weight:800;color:${col};cursor:pointer">${city.risk_score}</div>`,
      iconSize:[32,32], iconAnchor:[16,16],
    });
    const popup = `<div class="map-popup">
      <div class="map-popup-city">${city.city}</div>
      <div class="map-popup-row"><span>Risk</span><span style="color:${col};font-weight:700">${riskLabel(city.risk_score)} (${city.risk_score})</span></div>
      <div class="map-popup-row"><span>Rain</span><span>${city.rainfall||0} mm/hr</span></div>
      <div class="map-popup-row"><span>Temp</span><span>${city.temp||"—"}°C</span></div>
      <div class="map-popup-row"><span>AQI</span><span>${city.aqi||"—"} · ${city.aqi_level||"—"}</span></div>
      <div class="map-popup-row"><span>Demand</span><span>${city.demand_score}/100</span></div>
      <div class="map-popup-rec">💡 ${city.risk_score>70?"Switch to indoor delivery. High risk conditions.":city.risk_score>45?"Moderate conditions — monitor weather.":"Safe to work. Good earning window."}</div>
    </div>`;
    const m = L.marker([city.lat, city.lng], {icon})
      .bindPopup(popup, {maxWidth:240}).addTo(leafletMap);
    m.on("click", () => showCityPanel(city));
    leafletMarkers.push(m);
  });
  $("map-last-updated").textContent = "Updated: " + new Date().toLocaleTimeString();
  updateStatusTime();
}
function showCityPanel(c) {
  const col = riskColor(c.risk_score);
  const rec = c.risk_score > 70
    ? "⚠ Switch to indoor delivery — extreme conditions."
    : c.risk_score > 45 ? "🟡 Moderate risk. Carry rain gear."
    : "✅ Safe conditions. Peak earning window.";
  $("city-detail").innerHTML = `
    <h3 style="margin-bottom:0.75rem">${c.city}</h3>
    <div class="detail-row"><span class="detail-key">Risk Level</span><span class="detail-val" style="color:${col}">${riskLabel(c.risk_score)} (${c.risk_score}/100)</span></div>
    <div class="detail-row"><span class="detail-key">Demand Score</span><span class="detail-val">${c.demand_score}/100</span></div>
    <div class="detail-row"><span class="detail-key">Rainfall</span><span class="detail-val">${c.rainfall||0} mm/hr</span></div>
    <div class="detail-row"><span class="detail-key">Temperature</span><span class="detail-val">${c.temp||"—"}°C</span></div>
    <div class="detail-row"><span class="detail-key">AQI</span><span class="detail-val">${c.aqi||"—"} (${c.aqi_level||"—"})</span></div>
    <div class="detail-row"><span class="detail-key">Avg Payout</span><span class="detail-val">${inr(c.avg_payout)}</span></div>
    <div style="margin-top:0.8rem;padding:0.6rem;background:var(--bg-card2);border-radius:7px;font-size:0.8rem;color:var(--text-muted);line-height:1.5">${rec}</div>`;
}

// ─── CLAIMS ───────────────────────────────────────────────────
$("file-claim-btn").addEventListener("click", async () => {
  if (!currentUser) return;
  const claim_type  = $("claim-type").value;
  const amount      = parseInt($("claim-amount").value) || 3000;
  const description = $("claim-desc").value;
  $("file-claim-btn").textContent = "PROCESSING...";
  $("file-claim-btn").disabled    = true;
  $("claim-result-msg").innerHTML = "";
  animatePipeline();
  try {
    const data = await post("/claim/process", {
      user_id: currentUser.user_id, claim_type, amount, description,
    });
    const ok = data.auto_approved;
    $("claim-result-msg").innerHTML = `<div class="${ok?"claim-result-ok":"claim-result-warn"}">
      ${data.message}
      ${data.explanation ? `<div style="margin-top:0.4rem;font-size:0.77rem;opacity:0.8">🧠 ${data.explanation}</div>` : ""}
    </div>`;
    showTrustScore(data.fraud_score||75, ok, data.explanation);
    showFraudPanel(data);
    if (ok && data.claim_id) startUPIPayoutFlow(data.claim_id, amount);
    loadClaims();
  } catch (_) {
    $("claim-result-msg").innerHTML = '<div class="error-msg">Claim failed. Please try again.</div>';
    resetPipeline();
  } finally {
    $("file-claim-btn").textContent = "FILE CLAIM";
    $("file-claim-btn").disabled    = false;
  }
});
function animatePipeline() {
  const ids = ["pipe-rain","pipe-trigger","pipe-loss","pipe-fraud","pipe-payout"];
  ids.forEach(id => { const el=$(id); if(el) el.classList.remove("active","done"); });
  ids.forEach((id,i) => setTimeout(() => {
    if (i > 0) { const p=$(ids[i-1]); if(p){p.classList.remove("active");p.classList.add("done");} }
    const el=$(id); if(el) el.classList.add("active");
    if (i===ids.length-1) setTimeout(()=>{ const e=$(id); if(e){e.classList.remove("active");e.classList.add("done");} }, 700);
  }, i*550));
}
function resetPipeline() {
  ["pipe-rain","pipe-trigger","pipe-loss","pipe-fraud","pipe-payout"].forEach(id => {
    const el=$(id); if(el) el.classList.remove("active","done");
  });
}
function showTrustScore(pct, approved, reason) {
  const c = approved ? pct : Math.min(pct, 48);
  const box = $("trust-score-box");
  if (box) {
    box.style.display = "block";
    const val = $("trust-score-val");
    const bar = $("trust-score-bar");
    const rst = $("trust-reason");
    if (val) { val.textContent = c + "% Confidence"; val.style.color = approved ? "var(--success)" : "var(--warning)"; }
    if (bar) { bar.style.width = c + "%"; bar.style.background = approved ? "var(--success)" : "var(--warning)"; }
    if (rst) rst.textContent = reason || (approved ? "Environmental data corroborates claim. Auto-approved." : "Claim requires manual review.");
  }
}

function showFraudPanel(data) {
  const panel = $("fraud-panel");
  if (!panel) return;
  const breakdown = data.signal_breakdown || {};
  const weights   = data.signal_weights   || {};
  const labels = {
    weather_correlation:  "Weather Correlation",
    amount_anomaly:       "Amount Anomaly Check",
    claim_frequency:      "Claim Frequency",
    gps_movement_pattern: "GPS Movement Pattern",
    session_timing:       "Session Timing",
    device_fingerprint:   "Device Fingerprint",
  };
  const signalRows = Object.entries(breakdown).map(([key, val]) => {
    const col = val > 70 ? "var(--success)" : val > 45 ? "var(--warning)" : "var(--danger)";
    const w   = weights[key] || 0;
    return `<div style="display:flex;align-items:center;gap:.6rem;padding:.3rem 0;border-bottom:1px solid var(--border)">
      <span style="flex:1;font-size:.72rem;color:var(--text-muted)">${labels[key]||key}</span>
      <div style="width:80px;height:4px;background:var(--bg-card2);border-radius:99px"><div style="height:100%;width:${val}%;background:${col};border-radius:99px"></div></div>
      <span style="font-size:.72rem;font-weight:700;color:${col};min-width:30px">${val}%</span>
      <span style="font-size:.65rem;color:var(--text-dim);min-width:36px">w:${w}%</span>
    </div>`;
  }).join("");
  const trust = data.fraud_score || 75;
  const col = trust > 78 ? "var(--success)" : trust > 55 ? "var(--warning)" : "var(--danger)";
  $("fraud-trust-score").textContent = `Trust: ${trust}%`;
  $("fraud-trust-score").style.color  = col;
  $("fraud-signals-grid").innerHTML   = signalRows;
  panel.style.display = "block";
}

async function startUPIPayoutFlow(claimId, amount) {
  const panel = $("upi-payout-panel");
  if (!panel) return;
  try {
    const payout = await post("/payout/initiate", {
      user_id: currentUser.user_id, claim_id: claimId, amount,
    });
    const txnId = payout.txn_id;
    renderUPIPipeline(payout);
    // Advance through states
    const states = ["PROCESSING","FRAUD_CHECK","APPROVED","SUCCESS"];
    const delays = [1500, 3500, 5000, 8500];
    states.forEach((state, i) => {
      setTimeout(async () => {
        try {
          const updated = await post(`/payout/advance/${txnId}`, {});
          renderUPIPipeline(updated);
        } catch (_) {}
      }, delays[i]);
    });
  } catch (e) { console.error("Payout:", e); }
}

function renderUPIPipeline(p) {
  const panel = $("upi-payout-panel");
  if (!panel) return;
  const states = ["INITIATED","PROCESSING","FRAUD_CHECK","APPROVED","SUCCESS"];
  const icons  = ["📋","⚙️","🧠","✅","💸"];
  const stateIdx = states.indexOf(p.state);
  const col = p.state === "SUCCESS" ? "var(--success)" : "var(--accent)";
  panel.innerHTML = `
    <div style="margin-bottom:.8rem">
      <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.4rem">
        <span style="font-size:1rem;font-weight:700;color:${col}">${p.state}</span>
        <span style="font-size:.7rem;color:var(--text-muted)">${p.txn_id}</span>
      </div>
      <div style="font-size:.78rem;color:var(--text-muted)">${p.message}</div>
    </div>
    <div style="display:flex;gap:.3rem;margin-bottom:.8rem">
      ${states.map((s,i)=>`
        <div style="flex:1;text-align:center">
          <div style="font-size:1.1rem;opacity:${i<=stateIdx?1:.3}">${icons[i]}</div>
          <div style="height:3px;background:${i<=stateIdx?"var(--accent)":"var(--border)"};border-radius:99px;margin:.25rem 0;transition:background .4s"></div>
          <div style="font-size:.55rem;color:${i<=stateIdx?"var(--accent)":"var(--text-dim)"};text-transform:uppercase;letter-spacing:.04em">${s.replace("_"," ")}</div>
        </div>`).join("")}
    </div>
    <div style="display:flex;justify-content:space-between;font-size:.75rem;color:var(--text-muted)">
      <span>Amount: <strong style="color:var(--success)">${inr(p.amount)}</strong></span>
      <span>UPI: <strong>${p.upi_id}</strong></span>
      <span>Bank: ${p.bank}</span>
    </div>
    ${p.state==="SUCCESS"?`<div style="margin-top:.7rem;padding:.5rem .8rem;background:var(--success-dim);border:1px solid rgba(34,197,94,.2);border-radius:7px;font-size:.78rem;color:var(--success);font-weight:600">✅ ${inr(p.amount)} credited successfully to ${p.upi_id}</div>`:""}`;
}

async function loadClaims() {
  if (!currentUser) return;
  try {
    const claims = await api(`/claims/${currentUser.user_id}`);
    const el = $("claims-history");
    if (!claims || !claims.length) { el.innerHTML='<div class="loading">No claims yet.</div>'; return; }
    el.innerHTML = [...claims].reverse().map(c => {
      const cls = c.status==="AUTO_APPROVED"?"status-auto":c.status==="APPROVED"?"status-approved":"status-flagged";
      return `<div class="claim-item">
        <div class="claim-header">
          <span class="claim-id">#${c.claim_id}</span>
          <span class="claim-status ${cls}">${c.status}</span>
        </div>
        <div class="claim-meta">${(c.claim_type||"").replace("_"," ").toUpperCase()} · ${inr(c.amount)} · ${c.fraud_score}% confidence</div>
        ${c.explanation ? `<div class="claim-explain">🧠 ${c.explanation}</div>` : ""}
        ${c.flags?.length ? `<div class="claim-meta" style="color:var(--warning)">⚠ ${c.flags.join(", ")}</div>` : ""}
      </div>`;
    }).join("");
  } catch (e) { console.error("Claims:", e); }
}

// ─── INSIGHTS ─────────────────────────────────────────────────
async function loadInsights() {
  if (!currentUser) return;
  try {
    const city = currentUser.city || "Mumbai";
    const settled = await Promise.allSettled([
      api(`/insights?user_id=${currentUser.user_id}`),
      api(`/ml/explain-risk?user_id=${currentUser.user_id}`),
      api(`/ml/predict-loss?user_id=${currentUser.user_id}`),
      api(`/ai/protection-plan?user_id=${currentUser.user_id}`),
      api(`/ml/observatory`),
      api(`/fraud/gps-trace?user_id=${currentUser.user_id}&claim_type=rain`),
      api(`/ml/weather-baseline?city=${encodeURIComponent(city)}&claim_type=rain`),
    ]);
    const val = (i) => settled[i].status === "fulfilled" ? settled[i].value : null;
    const insights  = val(0);
    const mlExplain = val(1);
    const mlLoss    = val(2);
    const protPlan  = val(3);
    const obsData   = val(4);
    const gpsData   = val(5);
    const wbData    = val(6);

    if (insights) {
      renderAIExplanation(insights);
      renderEarningsChart(insights.weekly_earnings);
      renderRiskTrend(insights.risk_exposure_trend, insights.days);
      renderPersonalInsightsFromInsights(insights);
      renderWeeklyRecsFromInsights(insights);
      renderMetricsFromInsights(insights);
    }
    if (obsData)   renderMLObservatory(obsData);
    if (gpsData)   renderGPSIntelligence(gpsData, wbData);
    if (mlExplain) renderMLExplain(mlExplain);
    if (mlLoss)    renderMLLossPanel(mlLoss);
    if (protPlan)  renderProtectionPlan(protPlan);

    const upd = $("insights-last-updated");
    if (upd) upd.textContent = "Updated " + new Date().toLocaleTimeString();
  } catch (e) { console.error("Insights:", e); }
}

// ─── ML OBSERVATORY RENDERING ─────────────────────────────────
function renderMLObservatory(data) {
  if (!data) return;
  const curves = data.training_curves || {};
  const epochs = curves.epochs || [];

  // Draw training loss curve
  setTimeout(() => {
    drawLossCurve("obs-loss-canvas", epochs, curves.train_loss, curves.val_loss, curves.val_accuracy);
    drawROCCurve("obs-roc-canvas", data.roc_curve?.fpr, data.roc_curve?.tpr, data.final_metrics?.auc_roc);
    renderSHAPChart("obs-shap", data.feature_shap || []);
    renderConfusionMatrix("obs-confusion", data.confusion_matrix || {});
    renderObsPerf("obs-perf-row", data.final_metrics || {});
    renderModelVersions("obs-versions", data.model_versions || []);
  }, 100);
}

function drawLossCurve(canvasId, epochs, trainLoss, valLoss, valAcc) {
  const canvas = $(canvasId);
  if (!canvas || !trainLoss?.length) return;
  const W = canvas.offsetWidth || 380;
  const H = 190;
  canvas.width = W * 2; canvas.height = H * 2;
  canvas.style.width = W + "px"; canvas.style.height = H + "px";
  const ctx = canvas.getContext("2d");
  ctx.scale(2, 2);

  // Background
  ctx.fillStyle = "#050d1a";
  ctx.fillRect(0, 0, W, H);

  // Grid
  ctx.strokeStyle = "rgba(255,255,255,0.04)";
  ctx.lineWidth = 1;
  for (let x = 40; x < W; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
  for (let y = 20; y < H; y += 20) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

  const n = epochs.length;
  const pad = { l: 32, r: 12, t: 12, b: 24 };
  const cW = W - pad.l - pad.r;
  const cH = H - pad.t - pad.b;
  const allVals = [...trainLoss, ...valLoss];
  const minY = Math.min(...allVals) * 0.92;
  const maxY = Math.max(...allVals) * 1.05;

  function px(i)  { return pad.l + (i / (n - 1)) * cW; }
  function py(v)  { return pad.t + (1 - (v - minY) / (maxY - minY)) * cH; }

  // Axes labels
  ctx.fillStyle = "rgba(82,110,140,0.9)";
  ctx.font = "9px monospace";
  ctx.fillText("loss", 2, pad.t + 4);
  ctx.fillText("0", pad.l - 6, H - pad.b + 10);
  ctx.fillText("50", W - pad.r - 14, H - pad.b + 10);

  // Axis lines
  ctx.strokeStyle = "rgba(255,255,255,0.08)";
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(pad.l, pad.t); ctx.lineTo(pad.l, H - pad.b); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(pad.l, H - pad.b); ctx.lineTo(W - pad.r, H - pad.b); ctx.stroke();

  // Val accuracy (right axis, green, dashed, scaled)
  if (valAcc) {
    ctx.strokeStyle = "rgba(34,197,94,0.45)";
    ctx.lineWidth = 1.2;
    ctx.setLineDash([3, 4]);
    ctx.beginPath();
    valAcc.forEach((v, i) => {
      const accY = pad.t + (1 - (v - 0.55) / (1.0 - 0.55)) * cH;
      i === 0 ? ctx.moveTo(px(i), accY) : ctx.lineTo(px(i), accY);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Val loss (orange)
  ctx.strokeStyle = "#f59e0b";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  valLoss.forEach((v, i) => i === 0 ? ctx.moveTo(px(i), py(v)) : ctx.lineTo(px(i), py(v)));
  ctx.stroke();

  // Train loss (blue, filled)
  const grad = ctx.createLinearGradient(0, pad.t, 0, H - pad.b);
  grad.addColorStop(0, "rgba(79,126,247,0.35)");
  grad.addColorStop(1, "rgba(79,126,247,0.02)");
  ctx.fillStyle = grad;
  ctx.beginPath();
  trainLoss.forEach((v, i) => i === 0 ? ctx.moveTo(px(i), py(v)) : ctx.lineTo(px(i), py(v)));
  ctx.lineTo(px(n - 1), H - pad.b); ctx.lineTo(px(0), H - pad.b); ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "#4f7ef7";
  ctx.lineWidth = 2;
  ctx.beginPath();
  trainLoss.forEach((v, i) => i === 0 ? ctx.moveTo(px(i), py(v)) : ctx.lineTo(px(i), py(v)));
  ctx.stroke();

  // Convergence marker at epoch 47
  const bE = 46;
  ctx.strokeStyle = "rgba(34,197,94,0.7)";
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 3]);
  ctx.beginPath(); ctx.moveTo(px(bE), pad.t); ctx.lineTo(px(bE), H - pad.b); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = "#22c55e";
  ctx.font = "bold 8px monospace";
  ctx.fillText("Best: ep.47", px(bE) - 30, pad.t + 9);
}

function drawROCCurve(canvasId, fpr, tpr, auc) {
  const canvas = $(canvasId);
  if (!canvas || !fpr?.length) return;
  const W = canvas.offsetWidth || 380;
  const H = 190;
  canvas.width = W * 2; canvas.height = H * 2;
  canvas.style.width = W + "px"; canvas.style.height = H + "px";
  const ctx = canvas.getContext("2d");
  ctx.scale(2, 2);

  ctx.fillStyle = "#050d1a";
  ctx.fillRect(0, 0, W, H);

  const pad = { l: 28, r: 12, t: 12, b: 24 };
  const cW = W - pad.l - pad.r;
  const cH = H - pad.t - pad.b;

  function rx(v) { return pad.l + v * cW; }
  function ry(v) { return pad.t + (1 - v) * cH; }

  // Grid
  ctx.strokeStyle = "rgba(255,255,255,0.04)";
  ctx.lineWidth = 1;
  [0.25, 0.5, 0.75].forEach(v => {
    ctx.beginPath(); ctx.moveTo(rx(v), pad.t); ctx.lineTo(rx(v), H - pad.b); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(pad.l, ry(v)); ctx.lineTo(W - pad.r, ry(v)); ctx.stroke();
  });

  // Diagonal (random)
  ctx.strokeStyle = "rgba(255,255,255,0.15)";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  ctx.beginPath(); ctx.moveTo(rx(0), ry(0)); ctx.lineTo(rx(1), ry(1)); ctx.stroke();
  ctx.setLineDash([]);

  // ROC fill
  const grad = ctx.createLinearGradient(0, pad.t, 0, H - pad.b);
  grad.addColorStop(0, "rgba(79,126,247,0.3)");
  grad.addColorStop(1, "rgba(79,126,247,0.02)");
  ctx.fillStyle = grad;
  ctx.beginPath();
  fpr.forEach((f, i) => i === 0 ? ctx.moveTo(rx(f), ry(tpr[i])) : ctx.lineTo(rx(f), ry(tpr[i])));
  ctx.lineTo(rx(1), ry(0)); ctx.lineTo(rx(0), ry(0)); ctx.closePath();
  ctx.fill();

  // ROC curve
  ctx.strokeStyle = "#4f7ef7";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  fpr.forEach((f, i) => i === 0 ? ctx.moveTo(rx(f), ry(tpr[i])) : ctx.lineTo(rx(f), ry(tpr[i])));
  ctx.stroke();

  // AUC label
  ctx.fillStyle = "#4f7ef7";
  ctx.font = "bold 11px monospace";
  ctx.fillText(`AUC = ${auc || 0.9347}`, rx(0.3), ry(0.45));
  ctx.fillStyle = "rgba(82,110,140,0.9)";
  ctx.font = "8px monospace";
  ctx.fillText("FPR", W - pad.r - 20, H - pad.b + 10);
  ctx.fillText("TPR", pad.l - 22, pad.t + 8);
}

function renderSHAPChart(containerId, features) {
  const el = $(containerId);
  if (!el || !features?.length) return;
  const maxShap = Math.max(...features.map(f => f.shap));
  el.innerHTML = features.map(f => {
    const pct  = Math.round((f.shap / maxShap) * 100);
    const col  = f.direction === "positive" ? "#4f7ef7" : "#f05252";
    return `<div class="shap-row">
      <div class="shap-feature" title="${f.feature}">${f.feature}</div>
      <div class="shap-bar-track">
        <div class="shap-bar-fill" style="width:${pct}%;background:${col}"></div>
      </div>
      <div class="shap-pct" style="color:${col}">${f.pct}%</div>
    </div>`;
  }).join("");
}

function renderConfusionMatrix(containerId, cm) {
  const el = $(containerId);
  if (!el || !cm) return;
  const fmt = n => n >= 1000 ? (n / 1000).toFixed(1) + "K" : n;
  el.innerHTML = `
    <div class="obs-confusion">
      <div class="cm-cell cm-tp"><div class="cm-count">${fmt(cm.true_positive)}</div><div class="cm-label">True Positive</div></div>
      <div class="cm-cell cm-fp"><div class="cm-count">${fmt(cm.false_positive)}</div><div class="cm-label">False Positive</div></div>
      <div class="cm-cell cm-fn"><div class="cm-count">${fmt(cm.false_negative)}</div><div class="cm-label">False Negative</div></div>
      <div class="cm-cell cm-tn"><div class="cm-count">${fmt(cm.true_negative)}</div><div class="cm-label">True Negative</div></div>
    </div>`;
}

function renderObsPerf(containerId, m) {
  const el = $(containerId);
  if (!el || !m) return;
  el.innerHTML = [
    {k: "AUC-ROC",   v: m.auc_roc},
    {k: "F1 Score",  v: m.f1_score},
    {k: "Precision", v: m.precision},
    {k: "Recall",    v: m.recall},
    {k: "Accuracy",  v: m.accuracy},
  ].map(p => `<div class="obs-perf-pill">${p.k}: <span>${(p.v * 100).toFixed(1)}%</span></div>`).join("");
}

function renderModelVersions(containerId, versions) {
  const el = $(containerId);
  if (!el || !versions?.length) return;
  const maxAUC = Math.max(...versions.map(v => v.auc));
  el.innerHTML = `
    <div class="obs-ver-title">Model Evolution — from rule-based heuristics to Gradient Boosted Ensemble</div>
    <div class="ver-timeline">
      ${versions.map(v => {
        const barPct = Math.round((v.auc / maxAUC) * 100);
        const col = v.current ? "var(--accent)" : "var(--text-muted)";
        return `<div class="ver-node ${v.current ? "current" : ""}">
          <div class="ver-version">${v.version}</div>
          <div class="ver-auc" style="color:${col}">${(v.auc * 100).toFixed(1)}%</div>
          <div class="ver-bar" style="background:${col};opacity:.5;width:${barPct}%"></div>
          <div class="ver-date">${v.date}</div>
          <div class="ver-note">${v.note}</div>
          ${v.current ? '<div style="font-size:.6rem;color:var(--success);margin-top:.2rem;font-weight:700">▲ CURRENT</div>' : ""}
        </div>`;
      }).join("")}
    </div>`;
}

// ─── GPS INTELLIGENCE RENDERING ───────────────────────────────
function renderGPSIntelligence(gpsData, wbData) {
  if (!gpsData) return;

  const zone = gpsData.zone || {};
  const analysis = gpsData.analysis || {};
  const badge = $("gps-zone-badge");
  if (badge) badge.textContent = `Zone: ${zone.name || "Dharavi North"} · ${zone.precision || "10m²"} · ID: ${zone.zone_id || "MUM-DHR-N4-0047"}`;

  // GPS trace canvas
  setTimeout(() => {
    drawGPSTrace("gps-trace-canvas", gpsData.claimed_route, gpsData.actual_trace, analysis, zone);
  }, 120);

  // Analysis panel
  const panelEl = $("gps-analysis-panel");
  if (panelEl) {
    const isSpoof = analysis.spoofing_detected;
    const valCol  = isSpoof ? "var(--danger)" : "var(--success)";
    panelEl.innerHTML = `
      <div class="gps-verdict ${isSpoof ? "spoof" : "ok"}">
        ${isSpoof ? "⚠ GPS SPOOFING DETECTED" : "✓ GPS TRAJECTORY NOMINAL"}
      </div>
      <div class="gps-stat"><span class="gps-stat-key">Max Deviation</span><span class="gps-stat-val" style="color:${valCol}">${analysis.max_deviation_m}m</span></div>
      <div class="gps-stat"><span class="gps-stat-key">Teleportation Events</span><span class="gps-stat-val" style="color:${analysis.teleportation_events > 0 ? "var(--danger)" : "var(--success)"}">${analysis.teleportation_events}</span></div>
      ${isSpoof ? `<div class="gps-stat"><span class="gps-stat-key">Speed at Jump</span><span class="gps-stat-val" style="color:var(--danger)">${analysis.speed_at_jump_kmh} km/h</span></div>` : ""}
      <div class="gps-stat"><span class="gps-stat-key">GPS Consistency</span><span class="gps-stat-val">${analysis.gps_consistency_pct}%</span></div>
      <div class="gps-stat"><span class="gps-stat-key">Fraud Signal</span><span class="gps-stat-val" style="color:${isSpoof ? "var(--danger)" : "var(--success)"}">${analysis.fraud_signal}</span></div>
      <div class="gps-explain">${analysis.explanation}</div>`;
  }

  // Weather baseline chart
  if (wbData) {
    const wbEl = $("weather-baseline-chart");
    if (wbEl) {
      const b    = wbData.baseline_30d || [];
      const maxB = Math.max(...b, 1);
      wbEl.innerHTML = b.map((v, i) => {
        const isToday = i === b.length - 1;
        const col     = isToday ? (wbData.stats?.is_anomalous ? "#f05252" : "#22c55e") : "rgba(79,126,247,0.5)";
        const h       = Math.max(4, Math.round((v / maxB) * 44));
        return `<div class="wb-bar" style="height:${h}px;background:${col};${isToday ? "width:3px" : ""}"></div>`;
      }).join("");
    }
    const verdictEl = $("weather-baseline-verdict");
    if (verdictEl && wbData.stats) {
      const s = wbData.stats;
      verdictEl.className = "wb-verdict " + (s.is_anomalous ? "suspicious" : "consistent");
      verdictEl.textContent = s.explanation;
    }
  }
}

function drawGPSTrace(canvasId, claimed, actual, analysis, zone) {
  const canvas = $(canvasId);
  if (!canvas || !claimed?.length) return;
  const W = canvas.offsetWidth || 520;
  const H = 220;
  canvas.width = W * 2; canvas.height = H * 2;
  canvas.style.width = W + "px"; canvas.style.height = H + "px";
  const ctx = canvas.getContext("2d");
  ctx.scale(2, 2);

  // Background
  ctx.fillStyle = "#040c18";
  ctx.fillRect(0, 0, W, H);

  // Grid
  ctx.strokeStyle = "rgba(255,255,255,0.03)";
  ctx.lineWidth = 1;
  for (let x = 30; x < W; x += 30) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
  for (let y = 20; y < H; y += 20) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

  // Map bounds from claimed route
  const lats  = [...claimed.map(p => p.lat), ...actual.map(p => p.lat)];
  const lngs  = [...claimed.map(p => p.lng), ...actual.map(p => p.lng)];
  const minLat = Math.min(...lats), maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs), maxLng = Math.max(...lngs);
  const pad = { l: 32, r: 32, t: 28, b: 28 };
  const cW  = W - pad.l - pad.r;
  const cH  = H - pad.t - pad.b;

  function px(p) { return pad.l + ((p.lng - minLng) / (maxLng - minLng || 1)) * cW; }
  function py(p) { return H - pad.b - ((p.lat - minLat) / (maxLat - minLat || 1)) * cH; }

  // Zone label
  ctx.fillStyle = "rgba(79,126,247,0.12)";
  ctx.strokeStyle = "rgba(79,126,247,0.25)";
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.roundRect(6, 6, 200, 18, 4); ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#4f7ef7";
  ctx.font = "bold 8px monospace";
  ctx.fillText(`📍 ${zone?.name || "Dharavi North Sector 4"} · ${zone?.precision || "10m²"}`, 12, 18);

  // Coordinate labels
  ctx.fillStyle = "rgba(82,110,140,0.7)";
  ctx.font = "7px monospace";
  const firstPt = claimed[0];
  ctx.fillText(`${firstPt.lat}°N`, pad.l, H - 5);
  ctx.fillText(`${firstPt.lng}°E`, W - 70, H - 5);

  // Draw claimed route (blue)
  ctx.strokeStyle = "rgba(79,126,247,0.7)";
  ctx.lineWidth = 2;
  ctx.setLineDash([5, 3]);
  ctx.beginPath();
  claimed.forEach((p, i) => i === 0 ? ctx.moveTo(px(p), py(p)) : ctx.lineTo(px(p), py(p)));
  ctx.stroke();
  ctx.setLineDash([]);

  // Draw actual trace (red)
  ctx.strokeStyle = "#f05252";
  ctx.lineWidth = 2;
  ctx.beginPath();
  actual.forEach((p, i) => i === 0 ? ctx.moveTo(px(p), py(p)) : ctx.lineTo(px(p), py(p)));
  ctx.stroke();

  // Anomaly points (yellow rings)
  actual.forEach((p, i) => {
    if (!p.anomaly) return;
    const x = px(p), y = py(p);
    // Outer glow
    ctx.beginPath();
    ctx.arc(x, y, 8, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(245,158,11,0.2)";
    ctx.fill();
    ctx.strokeStyle = "#f59e0b";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    // Inner dot
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fillStyle = "#f59e0b";
    ctx.fill();
    // Label
    ctx.fillStyle = "#f59e0b";
    ctx.font = "bold 7px monospace";
    ctx.fillText("⚠", x - 3, y - 12);
  });

  // Start/end markers
  const start = claimed[0], end = claimed[claimed.length - 1];
  ctx.beginPath(); ctx.arc(px(start), py(start), 5, 0, Math.PI * 2);
  ctx.fillStyle = "#22c55e"; ctx.fill();
  ctx.beginPath(); ctx.arc(px(end), py(end), 5, 0, Math.PI * 2);
  ctx.fillStyle = "#f05252"; ctx.fill();

  ctx.fillStyle = "#22c55e"; ctx.font = "bold 8px sans-serif";
  ctx.fillText("A", px(start) + 7, py(start) + 4);
  ctx.fillStyle = "#f05252";
  ctx.fillText("B", px(end) + 7, py(end) + 4);

  // Spoofing annotation
  if (analysis?.spoofing_detected) {
    const midPt = actual[6] || actual[Math.floor(actual.length / 2)];
    if (midPt) {
      ctx.fillStyle = "rgba(240,82,82,0.12)";
      ctx.strokeStyle = "rgba(240,82,82,0.5)";
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 2]);
      ctx.beginPath(); ctx.roundRect(px(midPt) - 50, py(midPt) - 22, 100, 18, 4);
      ctx.fill(); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = "#f05252";
      ctx.font = "bold 7px monospace";
      ctx.fillText(`⚡ +${analysis.max_deviation_m}m in 1.84s`, px(midPt) - 44, py(midPt) - 9);
    }
  }
}

function renderAIExplanation(insights) {
  const textEl = $("ai-explanation-text");
  const metaEl = $("ai-explanation-meta");
  if (!textEl) return;

  const explanation = insights.ai_explanation || "AI analysis loading...";
  textEl.textContent = explanation;

  const cond = insights.conditions || {};
  const risk = cond.risk_score || 0;
  const col  = risk > 70 ? "var(--danger)" : risk > 45 ? "var(--warning)" : "var(--success)";

  if (metaEl) {
    metaEl.innerHTML = `
      <span style="color:var(--text-muted);font-size:.72rem">
        Rain ${cond.rainfall || 0}mm/hr ·
        AQI ${cond.aqi || "—"} ·
        ${cond.city || "—"} ·
        Risk <strong style="color:${col}">${risk}/100</strong> ·
        Model: NexaShift-AIEngine-v3.0
      </span>`;
  }
}

function renderRiskTrend(trend, days) {
  const el = $("risk-trend-chart");
  if (!el || !trend?.length) return;
  const maxV = Math.max(...trend, 1);
  const gradients = {
    danger:  "linear-gradient(180deg,#ff4d6a,rgba(255,77,106,0.55))",
    warning: "linear-gradient(180deg,#f7a832,rgba(247,168,50,0.55))",
    success: "linear-gradient(180deg,#10d97e,rgba(16,217,126,0.55))",
  };
  el.innerHTML = `
    <div class="risk-trend-bars">
      ${trend.map((v, i) => {
        const tier = v > 70 ? "danger" : v > 45 ? "warning" : "success";
        const col  = `var(--${tier})`;
        const pct  = Math.round((v / maxV) * 100);
        const dayLabel = (days || DAYS)[i] || "";
        return `<div class="rt-col">
          <div class="rt-val" style="color:${col}">${v}</div>
          <div class="rt-bar-space">
            <div class="rt-bar" style="height:${pct}%;background:${gradients[tier]}"></div>
          </div>
          <div class="rt-day">${dayLabel}</div>
        </div>`;
      }).join("")}
    </div>
    <div style="display:flex;align-items:center;justify-content:center;gap:1.25rem;margin-top:.65rem;font-size:.68rem;color:var(--text-muted)">
      <span style="display:flex;align-items:center;gap:.3rem"><span style="width:8px;height:8px;border-radius:2px;background:var(--success);display:inline-block"></span>Low (&lt;45)</span>
      <span style="display:flex;align-items:center;gap:.3rem"><span style="width:8px;height:8px;border-radius:2px;background:var(--warning);display:inline-block"></span>Medium (45–70)</span>
      <span style="display:flex;align-items:center;gap:.3rem"><span style="width:8px;height:8px;border-radius:2px;background:var(--danger);display:inline-block"></span>High (&gt;70)</span>
    </div>`;
}

function renderProtectionPlan(plan) {
  const el  = $("protection-plan-content");
  const btn = $("protection-risk-window");
  if (!el || !plan) return;

  const win = plan.risk_window || "LOW";
  const col = win === "HIGH" ? "var(--danger)" : win === "MODERATE" ? "var(--warning)" : "var(--success)";
  if (btn) { btn.textContent = win + " RISK WINDOW"; btn.style.color = col; }

  el.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.9rem;margin-bottom:1rem">
      <div class="prot-stat-box">
        <div class="psb-icon">⏰</div>
        <div class="psb-label">Safe Hours</div>
        <div class="psb-val">${(plan.safe_hours || []).join(", ")}</div>
      </div>
      <div class="prot-stat-box">
        <div class="psb-icon">⛔</div>
        <div class="psb-label">Avoid Hours</div>
        <div class="psb-val" style="color:var(--danger)">${(plan.avoid_hours || []).join(", ")}</div>
      </div>
      <div class="prot-stat-box">
        <div class="psb-icon">💰</div>
        <div class="psb-label">Expected Savings</div>
        <div class="psb-val" style="color:var(--success)">${inr(plan.expected_savings || 0)}/day</div>
      </div>
    </div>
    <div class="prot-switch-row">
      <div class="prot-switch-icon">🔄</div>
      <div>
        <div style="font-weight:700;font-size:.85rem">${plan.recommended_switch || "—"}</div>
        <div style="font-size:.72rem;color:var(--text-muted)">${plan.switch_reason || ""}</div>
      </div>
    </div>
    <div class="prot-ai-action">
      <span class="prot-ai-icon">🤖</span>
      <span>${plan.ai_action || "—"}</span>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:.7rem;margin-top:.8rem">
      <div class="prot-cov-chip ${plan.coverage_plan?.rain_coverage ? 'cov-on' : 'cov-off'}">
        🌧 Rain Coverage: ${plan.coverage_plan?.rain_coverage ? "ACTIVE" : "Standby"}
      </div>
      <div class="prot-cov-chip ${plan.coverage_plan?.aqi_coverage ? 'cov-on' : 'cov-off'}">
        😷 AQI Coverage: ${plan.coverage_plan?.aqi_coverage ? "ACTIVE" : "Standby"}
      </div>
      <div class="prot-cov-chip ${plan.coverage_plan?.heat_coverage ? 'cov-on' : 'cov-off'}">
        🌡 Heat Coverage: ${plan.coverage_plan?.heat_coverage ? "ACTIVE" : "Standby"}
      </div>
      <div class="prot-cov-chip ${plan.coverage_plan?.auto_claim_ready ? 'cov-on' : 'cov-off'}">
        ⚡ Auto-Claim: ${plan.coverage_plan?.auto_claim_ready ? "READY" : "Monitoring"}
      </div>
    </div>`;
}

function renderPersonalInsightsFromInsights(insights) {
  const perf   = insights.performance || {};
  const cond   = insights.conditions || {};
  const claims = insights.claim_stats || {};
  const trend  = (perf.weekly_total||0) > 0 ? "📈 Upward" : "📉 Downward";
  $("personal-insights").innerHTML = [
    {icon:"💰", title:"Avg Daily Earnings",  value:inr(perf.avg_daily_income||0),   desc:"Based on last 7 days"},
    {icon:"🏆", title:"Best Day This Week",  value:inr(perf.best_day||0),           desc:"Your peak performance"},
    {icon:"📉", title:"Lowest Day",          value:inr(perf.worst_day||0),          desc:"Room to improve"},
    {icon:"📊", title:"Earnings Trend",      value:perf.trend_direction || trend,   desc:"Week-over-week direction"},
    {icon:"📋", title:"Claims Filed",        value:claims.total_claims||0,          desc:`${claims.approval_rate||0}% approval rate`},
    {icon:"⚡", title:"Risk Rating",         value:(cond.risk_score||0)+"/100",     desc:"Current exposure level"},
  ].map(c=>`
    <div class="insight-card">
      <div class="insight-icon">${c.icon}</div>
      <div class="insight-title">${c.title}</div>
      <div class="insight-value">${c.value}</div>
      <div class="insight-desc">${c.desc}</div>
    </div>`).join("");
}

function renderWeeklyRecsFromInsights(insights) {
  const recs = insights.recommendations || [];
  $("weekly-recommendations").innerHTML = recs.map((r,i) => `
    <div class="rec-item">
      <div class="rec-num">${i+1}</div>
      <div>
        <div class="rec-text">${r.text}</div>
        <div class="rec-impact">${r.impact}</div>
      </div>
    </div>`).join("");
}

function renderMetricsFromInsights(insights) {
  const perf   = insights.performance || {};
  const claims = insights.claim_stats || {};
  $("performance-metrics").innerHTML = [
    {val:inr(perf.avg_daily_income||0),    label:"Avg Daily Earnings"},
    {val:inr(perf.weekly_total||0),        label:"7-Day Total Earnings"},
    {val:inr(perf.best_day||0),            label:"Best Day"},
    {val:claims.total_claims||0,           label:"Total Claims"},
    {val:inr(claims.total_payout||0),      label:"Total Payout Received"},
    {val:(claims.approval_rate||0)+"%",    label:"Claim Approval Rate"},
  ].map(m=>`
    <div style="background:var(--bg-card2);border:1px solid var(--border);border-radius:8px;padding:.85rem;text-align:center">
      <div style="font-size:1.2rem;font-weight:800;color:var(--accent)">${m.val}</div>
      <div style="font-size:.62rem;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted);margin-top:.2rem">${m.label}</div>
    </div>`).join("");
}
function renderEarningsChart(earnings) {
  const el = $("earnings-chart");
  if (!earnings?.length) return;
  const max = Math.max(...earnings);
  el.innerHTML = earnings.map((v,i) => `
    <div class="bar-col">
      <div class="bar-amt">${Math.round(v/1000)}k</div>
      <div class="bar-fill" style="height:${Math.round((v/max)*130)}px"></div>
      <div class="bar-day">${DAYS[i]}</div>
    </div>`).join("");
}
function renderMLExplain(data) {
  const el = $("ml-explain-content");
  if (!el) return;
  const contribs = data.feature_contributions || {};
  const inputs   = data.live_inputs || data.feature_inputs || {};
  const maxC = Math.max(...Object.values(contribs), 1);
  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:1rem;margin-bottom:.9rem;flex-wrap:wrap">
      <div>
        <div style="font-size:1.8rem;font-weight:800;color:${data.risk_score>70?"var(--danger)":data.risk_score>45?"var(--warning)":"var(--success)"}">${data.risk_score}<span style="font-size:.85rem;font-weight:400;color:var(--text-muted)">/100</span></div>
        <div style="font-size:.65rem;text-transform:uppercase;letter-spacing:.07em;color:var(--text-muted)">Risk Score</div>
      </div>
      <div style="flex:1;min-width:160px">
        <div style="font-size:.7rem;color:var(--text-muted);margin-bottom:.5rem">Live Inputs: Rain ${inputs.rainfall||0}mm · AQI ${inputs.aqi||100} · Hour ${inputs.hour}:00 · ${inputs.city}</div>
        ${Object.entries(contribs).map(([name,val])=>`
          <div style="margin-bottom:.3rem">
            <div style="display:flex;justify-content:space-between;font-size:.7rem;margin-bottom:.15rem"><span style="color:var(--text-muted)">${name}</span><span style="font-weight:700">${val}</span></div>
            <div style="height:4px;background:var(--bg-card2);border-radius:99px"><div style="height:100%;width:${Math.round(val/maxC*100)}%;background:var(--accent);border-radius:99px"></div></div>
          </div>`).join("")}
      </div>
    </div>
    <div style="font-size:.72rem;color:var(--text-muted)">Model: ${data.model_version} · Confidence: ${data.confidence_pct}%</div>`;
}

function renderMLLossPanel(data) {
  const el = $("ml-loss-panel");
  if (!el || !data) return;
  const metrics = [
    {label:"Daily Income", val:inr(data.daily_income),           col:"var(--text)"},
    {label:"Risk Probability", val:data.risk_probability_pct+"%", col:"var(--warning)"},
    {label:"Disruption Factor", val:data.disruption_factor,       col:"var(--accent)"},
    {label:"Predicted Loss",    val:inr(data.predicted_loss),     col:"var(--danger)"},
    {label:"NexaShift Payout",  val:inr(data.nexashift_payout),  col:"var(--success)"},
    {label:"Protected Income",  val:inr(data.net_protected_income), col:"var(--success)"},
    {label:"Without Protection",val:inr(data.unprotected_income), col:"var(--danger)"},
    {label:"Protection Benefit",val:inr(data.protection_benefit), col:"var(--accent)"},
  ];
  el.innerHTML = metrics.map(m=>`
    <div style="background:var(--bg-card2);border:1px solid var(--border);border-radius:8px;padding:.8rem;text-align:center">
      <div style="font-size:1.1rem;font-weight:800;color:${m.col}">${m.val}</div>
      <div style="font-size:.62rem;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted);margin-top:.2rem">${m.label}</div>
    </div>`).join("");
}
function renderPersonalInsights(summary) {
  const weekly = summary.weekly_earnings || [];
  const avg    = weekly.length ? Math.round(weekly.reduce((a,b)=>a+b,0)/weekly.length) : 0;
  const best   = weekly.length ? Math.max(...weekly) : 0;
  const worst  = weekly.length ? Math.min(...weekly) : 0;
  const trend  = weekly.length>=2 ? (weekly[weekly.length-1]>weekly[weekly.length-2] ? "📈 Upward" : "📉 Downward") : "—";
  $("personal-insights").innerHTML = [
    {icon:"💰",title:"Avg Daily Earnings", value:inr(avg),               desc:"Based on last 7 days"},
    {icon:"🏆",title:"Best Day This Week", value:inr(best),              desc:"Your peak performance"},
    {icon:"📉",title:"Lowest Day",         value:inr(worst),             desc:"Room to improve"},
    {icon:"📊",title:"Earnings Trend",     value:trend,                  desc:"Week-over-week direction"},
    {icon:"🛡",title:"Protection Level",   value:inr(summary.coverage),  desc:"Active income shield"},
    {icon:"⚡",title:"Risk Rating",        value:summary.risk_score+"/100",desc:"Current exposure"},
  ].map(c=>`
    <div class="insight-card">
      <div class="insight-icon">${c.icon}</div>
      <div class="insight-title">${c.title}</div>
      <div class="insight-value">${c.value}</div>
      <div class="insight-desc">${c.desc}</div>
    </div>`).join("");
}
function renderWeeklyRecs(summary) {
  $("weekly-recommendations").innerHTML = [
    {text:"Shift 40% of hours to 7–9 AM and 6–8 PM for peak demand windows", impact:"+12–18% daily income potential"},
    {text:`File preemptive claims during high-AQI days to recover protection faster`, impact:"Avg ₹2,400 recovered per event"},
    {text:summary.risk_score>60
      ?`Risk ${summary.risk_score} is elevated — consider switching to indoor delivery during storms`
      :`Risk ${summary.risk_score} is manageable. Maintain your current shift pattern.`, impact:"Reduces income volatility by 25%"},
    {text:"File claims within 24 hours of a disruption for best approval rates", impact:"Approval rate: 94% on-time vs 76% late"},
    {text:"Use Scenario Lab each morning to model rain and AQI before starting your shift", impact:"Avoid ₹800–1,200 unprotected loss days"},
  ].map((r,i)=>`
    <div class="rec-item">
      <div class="rec-num">${i+1}</div>
      <div>
        <div class="rec-text">${r.text}</div>
        <div class="rec-impact">${r.impact}</div>
      </div>
    </div>`).join("");
}
function renderMetrics(summary) {
  const weekly   = summary.weekly_earnings||[];
  const avgDaily = weekly.length ? Math.round(weekly.reduce((a,b)=>a+b,0)/weekly.length) : Math.round(summary.monthly_income/26);
  $("performance-metrics").innerHTML = [
    {val:inr(avgDaily),          label:"Avg Daily Earnings"},
    {val:`${summary.risk_score}/100`, label:"Live Risk Score"},
    {val:inr(summary.coverage),  label:"Total Coverage"},
    {val:inr(summary.premium),   label:"Monthly Premium"},
    {val:`${summary.claim_count}`,    label:"Claims Filed"},
    {val:summary.city,           label:"Operating City"},
  ].map(m=>`
    <div class="metric-box">
      <div class="metric-box-val">${m.val}</div>
      <div class="metric-box-label">${m.label}</div>
    </div>`).join("");
}

// ─── AI AUTOPILOT ─────────────────────────────────────────────
let autopilotInitialized = false;
function initAutopilot() {
  if (!currentUser) return;
  const toggle = $("autopilot-toggle");
  const label  = $("ap-toggle-label");
  const btn    = $("ap-generate-btn");
  if (!toggle || autopilotInitialized) return;
  autopilotInitialized = true;

  toggle.addEventListener("change", () => {
    const on = toggle.checked;
    label.textContent = on ? "ON" : "OFF";
    label.style.color = on ? "var(--success)" : "var(--text-muted)";
    if ($("ap-dot-nav")) $("ap-dot-nav").style.display = on ? "inline-block" : "none";
    post("/autopilot/toggle", { user_id: currentUser.user_id, enabled: on }).catch(()=>{});
    if (on) generateAutopilotPlan();
  });

  if (btn) btn.addEventListener("click", () => {
    toggle.checked = true;
    label.textContent = "ON";
    label.style.color = "var(--success)";
    if ($("ap-dot-nav")) $("ap-dot-nav").style.display = "inline-block";
    generateAutopilotPlan();
  });
}

async function generateAutopilotPlan() {
  if (!currentUser) return;
  $("autopilot-hero").innerHTML = `<div class="ap-hero-content"><div class="ap-hero-icon" style="animation:spin 1s linear infinite">⚙️</div><h3 class="ap-hero-title">AI computing your optimal shift plan...</h3><p class="ap-hero-sub">Analyzing live weather, AQI, demand curves, and your risk profile.</p></div>`;
  try {
    const data = await api(`/autopilot/plan?user_id=${currentUser.user_id}`);
    renderAutopilotPlan(data);
  } catch (e) {
    $("autopilot-hero").innerHTML = `<div class="ap-hero-content"><div class="ap-hero-icon">❌</div><h3 class="ap-hero-title">Error generating plan. Please try again.</h3></div>`;
  }
}

function renderAutopilotPlan(data) {
  $("autopilot-hero").style.display = "none";
  $("autopilot-plan-content").style.display = "block";

  // Summary card
  const risk = data.overall_risk || 0;
  const rCol = risk > 70 ? "var(--danger)" : risk > 45 ? "var(--warning)" : "var(--success)";
  $("ap-summary").innerHTML = `
    <div style="margin-bottom:.8rem">${data.narrative}</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:.7rem">
      <div style="background:var(--bg-card2);padding:.7rem;border-radius:8px;text-align:center">
        <div style="font-size:1.3rem;font-weight:800;color:var(--success)">${inr(data.estimated_earnings)}</div>
        <div style="font-size:.65rem;color:var(--text-muted);text-transform:uppercase">Safe Earnings</div>
      </div>
      <div style="background:var(--bg-card2);padding:.7rem;border-radius:8px;text-align:center">
        <div style="font-size:1.3rem;font-weight:800;color:${rCol}">${risk}/100</div>
        <div style="font-size:.65rem;color:var(--text-muted);text-transform:uppercase">Overall Risk</div>
      </div>
      <div style="background:var(--bg-card2);padding:.7rem;border-radius:8px;text-align:center">
        <div style="font-size:1.3rem;font-weight:800;color:var(--accent)">${data.work_hours_count}h</div>
        <div style="font-size:.65rem;color:var(--text-muted);text-transform:uppercase">Work Hours</div>
      </div>
    </div>
    <div style="margin-top:.8rem;font-size:.72rem;color:var(--text-muted)">
      🌧 Rain: ${data.weather_snapshot?.rainfall||0}mm · 🌫 AQI: ${data.weather_snapshot?.aqi||100} · 🌡 Temp: ${data.weather_snapshot?.temp||30}°C
    </div>`;

  // Recommendations
  const sw = data.switch_recommendation;
  $("ap-recs").innerHTML = `
    <div class="prot-item"><span class="prot-icon">⚡</span><div><div class="prot-title">Auto-Coverage: ${data.auto_coverage?"ACTIVE":"OFF"}</div><div class="prot-desc">Protection auto-activates during high-risk windows</div></div></div>
    <div class="prot-item"><span class="prot-icon">📅</span><div><div class="prot-title">${data.work_hours_count} work + ${data.rest_hours_count} avoid hours</div><div class="prot-desc">AI-scheduled based on live risk model</div></div></div>
    <div class="prot-item"><span class="prot-icon">🎯</span><div><div class="prot-title">Target: ${data.target_coverage_pct}% of daily goal</div><div class="prot-desc">Safe hours cover ${inr(data.estimated_earnings)} of ${inr(data.daily_target)} target</div></div></div>
    ${sw ? `<div class="prot-item"><span class="prot-icon">🔄</span><div><div class="prot-title">Switch to: ${sw.label}</div><div class="prot-desc">${sw.reason} · +${inr(sw.expected_gain)} extra</div></div></div>` : ""}`;

  // Schedule grid
  const schedule = data.schedule || [];
  $("ap-schedule-grid").innerHTML = schedule.map(s => `
    <div class="ap-slot" style="background:${s.color}14;border:1px solid ${s.color}40;border-radius:8px;padding:.5rem;text-align:center;min-width:52px">
      <div style="font-size:.65rem;color:var(--text-muted)">${s.label}</div>
      <div style="font-size:1rem">${s.icon}</div>
      <div style="font-size:.62rem;font-weight:700;color:${s.color}">${s.action}</div>
      <div style="font-size:.62rem;color:var(--text-muted)">${inr(s.earning_potential)}</div>
    </div>`).join("");

  // Chart
  const max = Math.max(...schedule.map(s=>s.earning_potential), 1);
  $("ap-chart").innerHTML = schedule.map(s => {
    const h = Math.round((s.earning_potential / max) * 96);
    return `<div class="proj-col"><div class="proj-bar" style="height:${h}px;background:${s.color};border-radius:4px 4px 0 0;width:18px;margin:0 2px"></div></div>`;
  }).join("");
  $("ap-chart-labels").innerHTML = schedule.map((s,i) =>
    `<div class="proj-label" style="font-size:.58rem">${i%2===0?s.label:""}</div>`).join("");
}

// ─── MAP ZONE TOGGLE ─────────────────────────────────────────
function setupMapToggle() {
  const cityBtn = $("map-city-btn");
  const zoneBtn = $("map-zone-btn");
  if (!cityBtn || !zoneBtn) return;
  cityBtn.addEventListener("click", () => {
    cityBtn.classList.add("active");
    zoneBtn.classList.remove("active");
    mapData = [];
    if (leafletMap) { leafletMap.remove(); leafletMap = null; }
    leafletMarkers = [];
    loadMap();
  });
  zoneBtn.addEventListener("click", async () => {
    zoneBtn.classList.add("active");
    cityBtn.classList.remove("active");
    if (!leafletMap) initLeafletMap();
    try {
      const zones = await api("/microzones/all");
      leafletMarkers.forEach(m => m.remove());
      leafletMarkers = [];
      zones.forEach(z => {
        const col = riskColor(z.risk);
        const icon = L.divIcon({
          className:"",
          html:`<div style="width:24px;height:24px;background:${col}22;border:1.5px solid ${col};border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:.55rem;font-weight:800;color:${col}">${z.risk}</div>`,
          iconSize:[24,24], iconAnchor:[12,12],
        });
        const rec = z.action === "WORK"
          ? "Prime earning zone — low risk, work now"
          : z.action === "OPTIONAL" ? "Moderate conditions — proceed with caution"
          : "Avoid this zone — high risk right now";
        const m = L.marker([z.lat, z.lng], {icon}).bindPopup(
          `<div class="map-popup"><div class="map-popup-city">${z.zone} <span style="color:var(--text-muted);font-size:.72rem">${z.city}</span></div>
           <div class="map-popup-row"><span>Risk</span><span style="color:${col};font-weight:700">${riskLabel(z.risk)} (${z.risk})</span></div>
           <div class="map-popup-row"><span>Demand</span><span>${z.demand}/100</span></div>
           <div class="map-popup-row"><span>Type</span><span>${z.type}</span></div>
           <div class="map-popup-rec">💡 ${rec}</div></div>`,
          {maxWidth:220}
        ).addTo(leafletMap);
        leafletMarkers.push(m);
      });
      $("map-last-updated").textContent = "Micro-zones · Updated: " + new Date().toLocaleTimeString();
    } catch (e) { console.error("Zones:", e); }
  });
}

// ─── DISRUPTION SIMULATOR ─────────────────────────────────────
let demoRainCanvas = null, demoRainCtx = null, demoRainAnim = null;

function initDemoMode() {
  const banner = $("demo-launcher-banner");
  if (banner) banner.style.display = "flex";

  const launchBtn = $("demo-launch-btn");
  if (launchBtn) launchBtn.addEventListener("click", openDisruptionDemo);

  const closeBtn = $("demo-close-btn");
  if (closeBtn) closeBtn.addEventListener("click", closeDisruptionDemo);

  const againBtn = $("demo-again-btn");
  if (againBtn) againBtn.addEventListener("click", resetDemoToPicker);

  const doneBtn = $("demo-done-btn");
  if (doneBtn) doneBtn.addEventListener("click", closeDisruptionDemo);

  document.querySelectorAll(".demo-scenario-card").forEach(card => {
    card.addEventListener("click", () => {
      const type = card.dataset.type;
      const rain = parseFloat(card.dataset.rain) || 0;
      const aqi  = parseFloat(card.dataset.aqi)  || 100;
      runDisruptionDemo(type, rain, aqi);
    });
  });
}

function openDisruptionDemo() {
  resetDemoToPicker();
  $("demo-modal").style.display = "flex";
  document.body.style.overflow  = "hidden";
}

function closeDisruptionDemo() {
  $("demo-modal").style.display = "none";
  document.body.style.overflow  = "";
  stopRainEffect();
}

function resetDemoToPicker() {
  $("demo-body-picker").style.display = "block";
  $("demo-body-flow").style.display   = "none";
  $("demo-progress-track").style.display = "none";
  $("demo-steps-row").style.display   = "none";
  $("demo-footer").style.display      = "none";
  $("demo-header-sub").textContent    = "Choose a disruption scenario to simulate the full AI pipeline";
  stopRainEffect();
  document.querySelectorAll(".demo-step-pill").forEach(p => {
    p.classList.remove("active", "done");
  });
}

function setDemoStep(n) {
  const pct = Math.round((n / 5) * 100);
  $("demo-progress-fill").style.width = pct + "%";
  document.querySelectorAll(".demo-step-pill").forEach(p => {
    const s = parseInt(p.dataset.step);
    p.classList.toggle("done",   s < n);
    p.classList.toggle("active", s === n);
    p.classList.remove("done"); // re-set below properly
    if (s < n)  p.classList.add("done");
    if (s === n) p.classList.add("active");
    if (s > n)  { p.classList.remove("done"); p.classList.remove("active"); }
  });
  // Activate/deactivate flow steps
  for (let i = 1; i <= 5; i++) {
    const el = $("dstep-" + i);
    if (!el) continue;
    el.classList.remove("active", "done", "dflow-pending");
    if (i < n)  el.classList.add("done");
    else if (i === n) el.classList.add("active");
    else el.classList.add("dflow-pending");
  }
}

function demoMarkStepDone(n, statusText, statusColor) {
  const statusEl = $("dflow-status-" + n);
  if (statusEl) {
    statusEl.innerHTML = `<span style="color:${statusColor};font-weight:800">${statusText}</span>`;
  }
}

async function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

const DEMO_LABELS = {
  rain:     { name: "Extreme Rainstorm", emoji: "🌧", claim_type: "rain",     amount: 3500, desc: "Extreme rain disruption — deliveries down 80%" },
  aqi:      { name: "AQI Hazard",        emoji: "😷", claim_type: "aqi",      amount: 2800, desc: "Hazardous AQI 310 — outdoor work unsafe" },
  platform: { name: "Platform Outage",   emoji: "📵", claim_type: "platform", amount: 2200, desc: "Swiggy/Zomato app outage — 3 hours downtime" },
  accident: { name: "Accident / Injury", emoji: "🚑", claim_type: "accident", amount: 4000, desc: "Emergency income replacement — injury reported" },
};

async function runDisruptionDemo(type, rain, aqi) {
  if (!currentUser) return;
  const cfg = DEMO_LABELS[type] || DEMO_LABELS.rain;

  // Switch to flow view
  $("demo-body-picker").style.display = "none";
  $("demo-body-flow").style.display   = "block";
  $("demo-progress-track").style.display = "block";
  $("demo-steps-row").style.display   = "flex";
  $("demo-header-sub").textContent    = cfg.name + " — AI pipeline running...";

  // Reset all content areas
  ["1","2","3","4","5"].forEach(i => {
    const c = $("dflow-content-" + i);
    if (c) c.style.display = "none";
    const s = $("dflow-status-" + i);
    if (s) s.innerHTML = '<div class="dflow-spinner"></div>';
    const sub = $("dflow-sub-" + i);
    if (sub && i !== "1") sub.textContent = "Waiting...";
  });
  const icon1 = $("dflow-icon-1");
  if (icon1) icon1.textContent = cfg.emoji;
  const t1 = $("dflow-title-1");
  if (t1) t1.textContent = cfg.name + " Detected";

  // Rain effect for rain/aqi scenarios
  if (type === "rain" || type === "aqi") startRainEffect(type);

  // ── STEP 1: Disruption detected ────────────────────────────
  setDemoStep(1);
  $("dflow-sub-1").textContent = "Scanning live conditions...";
  await delay(600);

  let scenarioData = null;
  try {
    scenarioData = await api(
      `/scenario-lab?user_id=${currentUser.user_id}&rain=${rain}&aqi=${aqi}&hour=${new Date().getHours()}`
    );
  } catch (_) {}

  const tempVal = 28 + Math.round(Math.random() * 8);
  const humVal  = type === "rain" ? 88 : 62;
  const windVal = type === "rain" ? 35 : 12;
  $("dflow-conditions").innerHTML = `
    <div class="dflow-cond-card"><div class="dflow-cond-icon">${type === "rain" ? "🌧" : type === "aqi" ? "😷" : type === "platform" ? "📵" : "🚑"}</div><div class="dflow-cond-label">${type === "rain" ? "Rainfall" : type === "aqi" ? "AQI Index" : type === "platform" ? "App Status" : "Incident"}</div><div class="dflow-cond-val danger">${type === "rain" ? rain + " mm/hr" : type === "aqi" ? aqi : type === "platform" ? "DOWN" : "REPORTED"}</div></div>
    <div class="dflow-cond-card"><div class="dflow-cond-icon">🌡</div><div class="dflow-cond-label">Temperature</div><div class="dflow-cond-val">${tempVal}°C</div></div>
    <div class="dflow-cond-card"><div class="dflow-cond-icon">💧</div><div class="dflow-cond-label">Humidity</div><div class="dflow-cond-val">${humVal}%</div></div>
    <div class="dflow-cond-card"><div class="dflow-cond-icon">💨</div><div class="dflow-cond-label">Wind</div><div class="dflow-cond-val">${windVal} km/h</div></div>
    <div class="dflow-cond-card"><div class="dflow-cond-icon">📍</div><div class="dflow-cond-label">City</div><div class="dflow-cond-val">${currentUser.city || "Mumbai"}</div></div>
    <div class="dflow-cond-card"><div class="dflow-cond-icon">⚡</div><div class="dflow-cond-label">Income Drop</div><div class="dflow-cond-val danger">${scenarioData ? scenarioData.income_drop_pct + "%" : "80%"}</div></div>
  `;
  $("dflow-content-1").style.display = "block";
  $("dflow-sub-1").textContent = "Disruption confirmed — auto-trigger activated";
  demoMarkStepDone(1, "✓ DETECTED", "var(--danger)");
  await delay(1200);

  // ── STEP 2: Claim auto-filed ────────────────────────────────
  setDemoStep(2);
  $("dflow-sub-2").textContent = "Filing claim automatically...";
  const claimAmount = cfg.amount;

  let claimData = null;
  try {
    claimData = await post("/claim/process", {
      user_id:     currentUser.user_id,
      claim_type:  cfg.claim_type,
      amount:      claimAmount,
      description: cfg.desc,
    });
  } catch (_) {}

  const trustScore = claimData?.fraud_score || claimData?.trust_score || 82;
  const claimId    = claimData?.claim_id    || ("CLM" + Date.now().toString().slice(-6));

  $("dflow-claim-details").innerHTML = `
    <div class="dflow-claim-row"><span class="ck">Claim ID</span><span class="cv">${claimId}</span></div>
    <div class="dflow-claim-row"><span class="ck">Type</span><span class="cv">${cfg.name}</span></div>
    <div class="dflow-claim-row"><span class="ck">Amount Requested</span><span class="cv" style="color:var(--warning)">₹${claimAmount.toLocaleString()}</span></div>
    <div class="dflow-claim-row"><span class="ck">Worker</span><span class="cv">${currentUser.name}</span></div>
    <div class="dflow-claim-row"><span class="ck">City</span><span class="cv">${currentUser.city || "Mumbai"}</span></div>
    <div class="dflow-claim-row"><span class="ck">Timestamp</span><span class="cv">${new Date().toLocaleTimeString()}</span></div>
  `;
  $("dflow-content-2").style.display = "block";
  $("dflow-sub-2").textContent = "Claim #" + claimId + " created and queued";
  demoMarkStepDone(2, "✓ FILED", "var(--accent)");
  await delay(1000);

  // ── STEP 3: Fraud analysis ──────────────────────────────────
  setDemoStep(3);
  $("dflow-sub-3").textContent = "Running 6-signal fraud analysis...";

  const signals = claimData?.signal_breakdown || {
    weather_correlation: 88, amount_anomaly: 72, claim_frequency: 90,
    gps_movement: 85, session_timing: 78, device_fingerprint: 95,
  };
  const weights = claimData?.signal_weights || {
    weather_correlation: 30, amount_anomaly: 20, claim_frequency: 20,
    gps_movement: 15, session_timing: 10, device_fingerprint: 5,
  };
  const sigLabels = {
    weather_correlation: "Weather Correlation",
    amount_anomaly:      "Amount Anomaly",
    claim_frequency:     "Claim Frequency",
    gps_movement:        "GPS Movement",
    session_timing:      "Session Timing",
    device_fingerprint:  "Device Fingerprint",
  };

  const sigKeys = Object.keys(sigLabels);
  let sigHTML = "";
  sigKeys.forEach(k => {
    const score  = signals[k]  || 80;
    const weight = weights[k]  || 10;
    const col    = score >= 70 ? "var(--success)" : score >= 45 ? "var(--warning)" : "var(--danger)";
    sigHTML += `<div class="dflow-signal-row">
      <span class="dflow-sig-label">${sigLabels[k]}</span>
      <div class="dflow-sig-bar-wrap"><div class="dflow-sig-bar" id="dsig-${k}" style="background:${col}"></div></div>
      <span class="dflow-sig-val" style="color:${col}">${score}</span>
      <span class="dflow-sig-weight">${weight}%</span>
    </div>`;
  });
  $("dflow-signals").innerHTML = sigHTML;
  $("dflow-content-3").style.display = "block";

  // Animate bars sequentially
  for (const k of sigKeys) {
    await delay(200);
    const bar = $("dsig-" + k);
    if (bar) bar.style.width = (signals[k] || 80) + "%";
  }
  await delay(400);

  // ── GPS + Weather baseline intelligence (new) ──────────────
  $("dflow-sub-3").textContent = "Running GPS trajectory analysis + historical weather comparison...";
  try {
    const city = currentUser?.city || "Mumbai";
    const claimType = cfg.type || "rain";
    const [gpsTrace, wbData] = await Promise.all([
      api(`/fraud/gps-trace?user_id=${currentUser.user_id}&claim_type=${claimType}`),
      api(`/ml/weather-baseline?city=${encodeURIComponent(city)}&claim_type=${claimType}`),
    ]);

    const gpsPanel = $("demo-gps-panel");
    if (gpsPanel) gpsPanel.style.display = "block";

    // Draw GPS trace on mini canvas
    setTimeout(() => {
      const demoCanvas = $("demo-gps-canvas");
      if (demoCanvas && gpsTrace) {
        drawGPSTrace("demo-gps-canvas", gpsTrace.claimed_route, gpsTrace.actual_trace, gpsTrace.analysis, gpsTrace.zone);
      }
    }, 80);

    // GPS verdict
    const verdictEl = $("demo-gps-verdict");
    if (verdictEl && gpsTrace?.analysis) {
      const isSpoof = gpsTrace.analysis.spoofing_detected;
      verdictEl.style.color = isSpoof ? "var(--danger)" : "var(--success)";
      verdictEl.textContent  = isSpoof
        ? `⚠ GPS_SPOOF — ${gpsTrace.analysis.max_deviation_m}m jump detected`
        : `✓ GPS_NOMINAL — ${gpsTrace.analysis.max_deviation_m}m max deviation`;
    }

    // Weather baseline bars
    if (wbData?.baseline_30d) {
      const barsEl = $("demo-wb-bars");
      const maxB   = Math.max(...wbData.baseline_30d, 1);
      if (barsEl) barsEl.innerHTML = wbData.baseline_30d.map((v, i) => {
        const isToday = i === wbData.baseline_30d.length - 1;
        const col = isToday ? (wbData.stats?.is_anomalous ? "#f05252" : "#22c55e") : "rgba(79,126,247,0.4)";
        const h = Math.max(3, Math.round((v / maxB) * 28));
        return `<div class="demo-wb-bar" style="height:${h}px;background:${col};flex:1"></div>`;
      }).join("");
      const wbText = $("demo-wb-verdict-text");
      if (wbText && wbData.stats) {
        const s = wbData.stats;
        wbText.style.color = s.is_anomalous ? "var(--danger)" : "var(--success)";
        wbText.textContent  = s.is_anomalous
          ? `⚠ SUSPICIOUS: Today ${s.today_rainfall_mm}mm vs 30-day mean ${s.mean_rainfall_mm}mm`
          : `✓ CONSISTENT: Today ${s.today_rainfall_mm}mm vs mean ${s.mean_rainfall_mm}mm`;
      }
    }
  } catch (e) { /* GPS panel stays hidden */ }

  await delay(600);
  $("dflow-sub-3").textContent = "All 6 fraud signals + GPS trace + weather baseline — analysis complete";
  demoMarkStepDone(3, "✓ CLEAN", "var(--success)");
  await delay(800);

  // ── STEP 4: AI decision ─────────────────────────────────────
  setDemoStep(4);
  $("dflow-sub-4").textContent = "NexaShift Decision Engine running...";
  await delay(700);

  const status   = claimData?.status || "AUTO_APPROVED";
  const approved = status === "AUTO_APPROVED";
  const payout   = claimData?.payout_amount || Math.round(claimAmount * 0.85);

  $("dflow-decision").innerHTML = `
    <div class="dflow-decision-badge ${approved ? "auto-approved" : "flagged"}">
      <div class="ddb-icon">${approved ? "✅" : "⚠️"}</div>
      <div>
        <div class="ddb-main" style="color:${approved ? "var(--success)" : "var(--warning)"}">${status.replace("_", " ")}</div>
        <div class="ddb-sub">${approved ? "Claim cleared — payout authorised immediately" : "Flagged for manual review — payout pending"}</div>
      </div>
    </div>
    <div class="dflow-trust-row">
      <span class="dflow-trust-label">Trust Score</span>
      <div class="dflow-trust-bar-wrap">
        <div class="dflow-trust-fill" id="dflow-trust-fill" style="width:0%;background:${approved ? "var(--success)" : "var(--warning)"}"></div>
      </div>
      <span class="dflow-trust-val" style="color:${approved ? "var(--success)" : "var(--warning)"}">${trustScore}</span>
    </div>
    <div style="margin-top:.65rem;font-size:.78rem;color:var(--text-muted)">
      Payout authorised: <strong style="color:var(--success)">₹${payout.toLocaleString()}</strong>
      · Model: <strong>NexaShift-FraudNet-v3.1</strong>
    </div>
  `;
  $("dflow-content-4").style.display = "block";
  await delay(100);
  const tf = $("dflow-trust-fill");
  if (tf) tf.style.width = trustScore + "%";
  $("dflow-sub-4").textContent = status.replace("_", " ") + " — trust score " + trustScore + "/100";
  demoMarkStepDone(4, "✓ " + (approved ? "APPROVED" : "FLAGGED"), approved ? "var(--success)" : "var(--warning)");
  await delay(1000);

  // ── STEP 5: UPI Payout ──────────────────────────────────────
  setDemoStep(5);
  $("dflow-sub-5").textContent = "Initiating UPI payout...";

  const upiStages = [
    { id:"INITIATED",   icon:"📤", label:"Initiated"    },
    { id:"PROCESSING",  icon:"⚙️",  label:"Processing"   },
    { id:"FRAUD_CHECK", icon:"🔍", label:"Fraud Check"  },
    { id:"APPROVED",    icon:"✅", label:"Approved"     },
    { id:"SUCCESS",     icon:"💚", label:"Credited"     },
  ];
  $("dflow-upi-stages").innerHTML = upiStages.map((s, i) => `
    <div class="dflow-upi-stage" id="upi-stage-${i}">
      <div class="upi-stage-icon">${s.icon}</div>
      <div>${s.label}</div>
    </div>
    ${i < upiStages.length - 1 ? '<div class="upi-stage-arrow">→</div>' : ""}
  `).join("");
  $("dflow-content-5").style.display = "block";

  // Animate each UPI stage
  let txnId = null;
  for (let i = 0; i < upiStages.length; i++) {
    const stageEl = $("upi-stage-" + i);
    // Mark previous done
    if (i > 0) {
      const prev = $("upi-stage-" + (i - 1));
      if (prev) { prev.classList.remove("upi-active"); prev.classList.add("upi-done"); }
    }
    if (stageEl) stageEl.classList.add("upi-active");
    $("dflow-sub-5").textContent = upiStages[i].label + "...";
    $("dflow-status-5").innerHTML = `<span style="color:var(--accent)">${upiStages[i].label}</span>`;

    // Hit the advance endpoint for intermediate steps
    if (txnId && i >= 1 && i <= 3) {
      try { await post(`/payout/advance/${txnId}`, {}); } catch (_) {}
    }
    if (i === 0 && currentUser) {
      try {
        const pr = await post("/payout/initiate", {
          user_id: currentUser.user_id, claim_id: claimId, amount: payout,
        });
        txnId = pr?.transaction_id || pr?.txn_id;
      } catch (_) {}
    }
    await delay(900);
  }
  // Final done state
  const last = $("upi-stage-" + (upiStages.length - 1));
  if (last) { last.classList.remove("upi-active"); last.classList.add("upi-done"); }

  $("dflow-upi-success").style.display = "block";
  $("upi-success-title").textContent   = "₹" + payout.toLocaleString() + " credited to your UPI!";
  $("upi-success-txn").textContent     = txnId ? "Txn ID: " + txnId : "Instant UPI transfer complete";
  $("dflow-sub-5").textContent = "₹" + payout.toLocaleString() + " credited — transfer complete";
  demoMarkStepDone(5, "✓ PAID", "var(--success)");

  // Progress to 100%
  setDemoStep(6);
  $("demo-progress-fill").style.width = "100%";
  $("demo-header-sub").textContent    = "Demo complete — full pipeline executed successfully ✅";

  stopRainEffect();
  $("demo-footer").style.display = "flex";
}

// ── Rain canvas effect ────────────────────────────────────────
function startRainEffect(type) {
  const canvas = $("rain-canvas");
  if (!canvas) return;
  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;
  canvas.style.display = "block";
  demoRainCtx = canvas.getContext("2d");

  const drops = Array.from({ length: type === "rain" ? 180 : 60 }, () => ({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    len:   8  + Math.random() * 16,
    speed: 12 + Math.random() * 14,
    alpha: 0.2 + Math.random() * 0.5,
    color: type === "rain" ? "99,179,255" : "255,165,0",
  }));

  function frame() {
    demoRainCtx.clearRect(0, 0, canvas.width, canvas.height);
    drops.forEach(d => {
      demoRainCtx.beginPath();
      demoRainCtx.strokeStyle = `rgba(${d.color},${d.alpha})`;
      demoRainCtx.lineWidth   = type === "rain" ? 1.2 : 0.8;
      demoRainCtx.moveTo(d.x, d.y);
      demoRainCtx.lineTo(d.x - 2, d.y + d.len);
      demoRainCtx.stroke();
      d.y += d.speed;
      if (d.y > canvas.height) { d.y = -d.len; d.x = Math.random() * canvas.width; }
    });
    demoRainAnim = requestAnimationFrame(frame);
  }
  frame();
}

function stopRainEffect() {
  if (demoRainAnim) { cancelAnimationFrame(demoRainAnim); demoRainAnim = null; }
  const canvas = $("rain-canvas");
  if (canvas) canvas.style.display = "none";
}

// ─── BOOT ─────────────────────────────────────────────────────
(async function boot() {
  const saved = localStorage.getItem("nexashift_user");
  if (saved) {
    try {
      const profile = JSON.parse(saved);
      // Re-hydrate the backend in case it restarted and lost in-memory state
      const res = await fetch("/restore-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });
      if (res.ok) {
        const data = await res.json();
        // Use the freshly-scored user object from the backend
        currentUser = data.user || profile;
        localStorage.setItem("nexashift_user", JSON.stringify(currentUser));
        initApp();
        return;
      }
    } catch (_) {}
  }
  showScreen("register");
})();
