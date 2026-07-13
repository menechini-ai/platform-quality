from __future__ import annotations

import asyncio
import os
import random
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

DD_API_KEY = os.environ.get("DATADOG_API_KEY", "")
DD_APP_KEY = os.environ.get("DATADOG_APP_KEY", "")
DD_SITE = os.environ.get("DATADOG_SITE", "datadoghq.com")
DD_API_BASE = f"https://api.{DD_SITE}"
DD_LOG_INTAKE = f"https://http-intake.logs.{DD_SITE}"

API_SERVICES = [
    {"name": "api-gateway", "env": "dev"},
    {"name": "api-gateway", "env": "prd"},
    {"name": "user-service", "env": "dev"},
    {"name": "user-service", "env": "prd"},
]

SANDBOX_MONITORS = [
    {
        "id": "health",
        "name": "Health Check",
        "type": "query alert",
        "query_tpl": "avg(last_5m):avg:{metric_svc}.health{{service:{service},env:{env}}} < 1",
        "message_tpl": "API {service} ({env}) health check failing — service not reporting",
        "thresholds": {"critical": 1.0},
    },
    {
        "id": "latency",
        "name": "High Latency",
        "type": "query alert",
        "query_tpl": "avg(last_5m):avg:{metric_svc}.latency_ms{{service:{service},env:{env}}} > 500",
        "message_tpl": "API {service} ({env}) latency above 500ms",
        "thresholds": {"critical": 500, "warning": 300},
    },
    {
        "id": "error_rate",
        "name": "High Error Rate",
        "type": "query alert",
        "query_tpl": "avg(last_5m):avg:{metric_svc}.error_rate{{service:{service},env:{env}}} > 0.05",
        "message_tpl": "API {service} ({env}) error rate above 5%",
        "thresholds": {"critical": 0.05, "warning": 0.02},
    },
    {
        "id": "no_traffic",
        "name": "No Traffic",
        "type": "query alert",
        "query_tpl": "avg(last_5m):avg:{metric_svc}.request_count{{service:{service},env:{env}}} < 1",
        "message_tpl": "API {service} ({env}) receiving no traffic",
        "thresholds": {"critical": 1, "warning": 5},
    },
    {
        "id": "cpu",
        "name": "High CPU Usage",
        "type": "query alert",
        "query_tpl": "avg(last_5m):avg:{metric_svc}.cpu_usage{{service:{service},env:{env}}} > 90",
        "message_tpl": "API {service} ({env}) CPU usage above 90%",
        "thresholds": {"critical": 90, "warning": 75},
    },
]

SEVERITIES = ["SEV-1", "SEV-2", "SEV-3", "SEV-4", "SEV-5"]
STATUSES = ["error", "warn", "info", "debug", "alert"]
ALERT_TYPES = ["error", "warning", "info", "success"]
FAILURE_PATTERNS = ["deploy", "resource", "latency", "dependency", "data_corruption"]
ERROR_MSGS = [
    "Connection timeout after 30s",
    "Database connection pool exhausted",
    "Rate limit exceeded for API key",
    "Invalid authentication token",
    "Memory usage exceeded threshold",
    "Null pointer exception in request handler",
    "SSL certificate verification failed",
]

app = FastAPI(title="Demo UI")


@app.get("/health")
async def health():
    return {"service": "demo-ui", "status": "ok"}


def _dd_headers() -> dict[str, str]:
    h = {"DD-API-KEY": DD_API_KEY, "Content-Type": "application/json"}
    if DD_APP_KEY:
        h["DD-APPLICATION-KEY"] = DD_APP_KEY
    return h


async def _dd_delete(c: httpx.AsyncClient, url: str, headers: dict) -> bool:
    # Retry on rate-limit/5xx so bulk cleanup never leaves resources behind.
    for attempt in range(6):
        try:
            dr = await c.delete(url, headers=headers)
        except Exception:
            await asyncio.sleep(min(2**attempt, 8))
            continue
        if dr.status_code in (200, 204, 404):
            return True
        if dr.status_code in (429, 500, 502, 503, 504):
            retry_after = dr.headers.get("retry-after")
            wait = (
                float(retry_after)
                if (retry_after and retry_after.isdigit())
                else min(2**attempt, 8) + random.uniform(0, 1)
            )
            await asyncio.sleep(wait)
            continue
        return False
    return False


def _tags(service: str, env: str = "demo") -> str:
    return f"service:{service},env:{env},team:observai,purpose:demo"


def _tag_list(service: str, env: str = "demo") -> list[str]:
    return [f"service:{service}", f"env:{env}", "team:observai", "purpose:demo"]


# Per sandbox-run session tag so monitors/SLOs/incidents stay scoped to one run.
# Incidents can't be deleted (only resolved), so this tag lets you filter them in Datadog.
CURRENT_SANDBOX_SESSION = ""


def _new_session() -> str:
    global CURRENT_SANDBOX_SESSION
    CURRENT_SANDBOX_SESSION = "sess-" + uuid.uuid4().hex[:8]
    return CURRENT_SANDBOX_SESSION


def _session_tag() -> str:
    return f"sandbox_session:{CURRENT_SANDBOX_SESSION}" if CURRENT_SANDBOX_SESSION else ""


async def _delete_sandbox_infra(c: httpx.AsyncClient, headers: dict) -> None:
    # Datadog allows duplicate monitor names, so each run would otherwise pile up.
    # Wipe existing [Sandbox] SLOs + monitors for a clean slate before creating.
    # SLOs first: a monitor linked to an SLO cannot be deleted (Datadog 400).
    try:
        r = await c.get(f"{DD_API_BASE}/api/v1/slo?query=%5BSandbox%5D", headers=headers)
        if r.status_code == 200:
            slos = r.json().get("data", [])
            if isinstance(slos, dict):
                slos = [slos]
            for s in slos:
                sid = s.get("id") if isinstance(s, dict) else None
                if sid:
                    await c.delete(f"{DD_API_BASE}/api/v1/slo/{sid}", headers=headers)
                    await asyncio.sleep(0.05)
    except Exception:
        pass
    try:
        r = await c.get(f"{DD_API_BASE}/api/v1/monitor", headers=headers)
        if r.status_code == 200:
            for m in r.json():
                if isinstance(m, dict) and m.get("name", "").startswith("[Sandbox]"):
                    mid = m.get("id")
                    if mid:
                        await c.delete(f"{DD_API_BASE}/api/v1/monitor/{mid}", headers=headers)
                        await asyncio.sleep(0.05)
    except Exception:
        pass


def _sandbox_api_list() -> list[dict[str, str]]:
    return [
        {"label": f"{s['name']} — {s['env']}", "service": s["name"], "env": s["env"]}
        for s in API_SERVICES
    ]


def _metric_prefix(service: str) -> str:
    return service.replace("-", "_")


HTML = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>API Sandbox — Demo</title>
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config={darkMode:'class',theme:{extend:{colors:{surface:{900:'#0f1117',800:'#161822',700:'#1c1f2e',600:'#24273a'},brand:{500:'#6366f1',400:'#818cf8',600:'#4f46e5'}}}}}
</script>
<style>
body{background:#0f1117;color:#e2e8f0;font-family:ui-monospace,SFMono-Regular,monospace}
.card{background:#161822;border:1px solid #1e293b;border-radius:12px;padding:1.25rem}
.card:hover{border-color:#334155}
input,select,textarea{background:#1c1f2e;border:1px solid #334155;border-radius:8px;padding:0.5rem 0.75rem;color:#e2e8f0;font-size:0.875rem;width:100%}
input:focus,select:focus{border-color:#6366f1;outline:none}
button{transition:all 0.15s}
.btn-primary{background:#4f46e5;color:white;padding:0.5rem 1rem;border-radius:8px;font-weight:600}
.btn-primary:hover{background:#6366f1}
.btn-primary:disabled{opacity:0.5;cursor:not-allowed}
.btn-secondary{background:#1e293b;color:#94a3b8;padding:0.5rem 1rem;border-radius:8px}
.btn-secondary:hover{background:#334155;color:#e2e8f0}
.btn-danger{background:#dc2626;color:white;padding:0.5rem 1rem;border-radius:8px;font-size:0.875rem}
.btn-danger:hover{background:#ef4444}
.btn-danger:disabled{opacity:0.5;cursor:not-allowed}
.badge{padding:0.125rem 0.5rem;border-radius:999px;font-size:0.75rem;font-weight:600}
.output-box{background:#0f1117;border:1px solid #1e293b;border-radius:8px;padding:0.75rem;font-size:0.75rem;max-height:200px;overflow:auto;white-space:pre-wrap;color:#94a3b8;font-family:monospace}
.card-ok{border-color:#059669!important;box-shadow:0 0 12px rgba(5,150,105,0.2)}
.card-error{border-color:#dc2626!important;box-shadow:0 0 12px rgba(220,38,38,0.2)}
#toast{position:fixed;top:1rem;right:1rem;z-index:9999;display:none;max-width:24rem;padding:0.75rem 1rem;border-radius:8px;font-size:0.875rem;font-weight:500;box-shadow:0 4px 24px rgba(0,0,0,0.4)}
#toast.show{display:block;animation:fadeIn 0.2s ease-out}
@keyframes fadeIn{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
.monitor-ok{color:#34d399}
.monitor-warn{color:#fbbf24}
.monitor-error{color:#f87171}
</style>
</head>
<body class="p-6 max-w-7xl mx-auto">

<div class="flex items-center justify-between mb-6">
  <div>
    <h1 class="text-2xl font-bold text-white">API Sandbox</h1>
    <p class="text-sm text-slate-500 mt-1">Sandbox com monitors Datadog para APIs (dev + prd)</p>
  </div>
  <span class="badge bg-emerald-500/20 text-emerald-400">SANDBOX</span>
</div>
<div id="toast"></div>

<div class="grid grid-cols-1 md:grid-cols-2 gap-4">

  <!-- ── Sandbox Card ── -->
  <div class="card">
    <h2 class="text-sm font-bold text-white mb-3 flex items-center gap-2">
      <span class="w-2 h-2 rounded-full bg-green-400"></span> Sandbox — Monitors
    </h2>
    <div class="space-y-3">
      <div class="text-xs text-slate-400">
        Cria 5 monitors vinculados às métricas reais das APIs para cada ambiente:
      </div>
      <div class="grid grid-cols-2 gap-1 text-xs text-slate-500 bg-surface-900 p-2 rounded-lg">
        <div>• Health (<span class="text-slate-300">health</span>)</div>
        <div>• Latency (<span class="text-slate-300">latency_ms</span>)</div>
        <div>• Error Rate (<span class="text-slate-300">error_rate</span>)</div>
        <div>• No Traffic (<span class="text-slate-300">request_count</span>)</div>
        <div class="col-span-2">• CPU Usage (<span class="text-slate-300">cpu_usage</span>)</div>
      </div>
      <div id="sandbox-apis" class="text-xs space-y-1">
        <div class="flex items-center gap-2 text-slate-300"><span class="w-2 h-2 rounded-full bg-brand-400"></span> api-gateway <span class="badge bg-blue-500/20 text-blue-400">dev</span></div>
        <div class="flex items-center gap-2 text-slate-300"><span class="w-2 h-2 rounded-full bg-brand-400"></span> api-gateway <span class="badge bg-orange-500/20 text-orange-400">prd</span></div>
        <div class="flex items-center gap-2 text-slate-300"><span class="w-2 h-2 rounded-full bg-brand-400"></span> user-service <span class="badge bg-blue-500/20 text-blue-400">dev</span></div>
        <div class="flex items-center gap-2 text-slate-300"><span class="w-2 h-2 rounded-full bg-brand-400"></span> user-service <span class="badge bg-orange-500/20 text-orange-400">prd</span></div>
      </div>
      <div class="flex gap-2">
        <button onclick="createSandbox()" id="sandbox-btn" class="btn-primary flex-1">Create Sandbox</button>
        <button onclick="cleanupSandbox()" id="cleanup-btn" class="btn-danger">Clean Up All</button>
      </div>
      <pre id="sandbox-out" class="output-box mt-2 h-32"></pre>
      <div id="sandbox-results" class="hidden text-xs space-y-1 mt-1"></div>
      <div id="sandbox-session" class="hidden text-xs text-slate-500 mt-1"></div>
    </div>
  </div>

  <!-- ── Incidents Card ── -->
  <div class="card">
    <h2 class="text-sm font-bold text-white mb-3 flex items-center gap-2">
      <span class="w-2 h-2 rounded-full bg-red-400"></span> Incidents
    </h2>
    <div class="space-y-2">
      <div><label class="text-xs text-slate-500 mb-1 block">API Service</label>
        <select id="api-select" onchange="updateIncidentFields()"></select>
      </div>
      <div><label class="text-xs text-slate-500 mb-1 block">Name</label><input type="text" id="inc-name" class="w-full"></div>
      <div><label class="text-xs text-slate-500 mb-1 block">Description</label><input type="text" id="inc-desc" class="w-full"></div>
      <div><label class="text-xs text-slate-500 mb-1 block">Tags</label><input type="text" id="inc-tags" readonly class="w-full text-slate-400"></div>
      <div class="grid grid-cols-2 gap-2">
        <div><label class="text-xs text-slate-500 mb-1 block">Quantity</label><input type="range" id="inc-qty" min="1" max="20" value="3" class="w-full" oninput="document.getElementById('inc-qty-val').textContent=this.value"><span id="inc-qty-val" class="text-xs text-brand-400">3</span></div>
        <div><label class="text-xs text-slate-500 mb-1 block">Interval</label><select id="inc-int"><option value="0">Simultaneous</option><option value="1">1s</option><option value="5">5s</option><option value="15">15s</option><option value="20">20s</option><option value="-1">Random</option></select></div>
      </div>
      <div><label class="text-xs text-slate-500 mb-1 block">Severity</label><select id="inc-sev"><option value="SEV-1">SEV-1 Critical</option><option value="SEV-2" selected>SEV-2</option><option value="SEV-3">SEV-3</option><option value="SEV-4">SEV-4</option><option value="SEV-5">SEV-5 Info</option></select></div>
      <div><label class="text-xs text-slate-500 mb-1 block">Take down before incident</label>
        <select id="down-duration" class="w-full text-sm"><option value="0">None (skip)</option><option value="5">5s</option><option value="10" selected>10s</option><option value="20">20s</option><option value="30">30s</option></select>
      </div>
      <div class="flex items-center gap-2"><input type="checkbox" id="inc-evidence" checked class="w-4 h-4"><label for="inc-evidence" class="text-xs text-slate-500">Generate evidence logs, metrics, events, monitors</label></div>
      <button onclick="runSeed()" class="btn-primary w-full mt-2">Create Incidents</button>
      <pre id="inc-out" class="output-box mt-2 h-20"></pre>
    </div>
  </div>

</div>

<!-- Activity Log -->
<div class="mt-6">
  <div class="flex items-center justify-between mb-2">
    <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider">Activity</h3>
    <button onclick="document.getElementById('activity').textContent=''" class="btn-secondary text-xs">Clear</button>
  </div>
  <pre id="activity" class="output-box h-40"></pre>
</div>

<script>
const API_LIST = [];
let currentSession = '';

function log(msg, type='info') {
  const el = document.getElementById('activity');
  if (!el) return;
  const t = new Date().toISOString().slice(11,19);
  const colors = {info:'#94a3b8',ok:'#34d399',error:'#f87171',warn:'#fbbf24'};
  el.innerHTML += '<span style="color:'+(colors[type]||colors.info)+'">['+t+']</span> '+msg+'\\n';
  el.scrollTop = el.scrollHeight;
  if (type === 'error') console.error('['+t+'] '+msg);
  else if (type === 'warn') console.warn('['+t+'] '+msg);
  else console.log('['+t+'] '+msg);
}

function toast(msg, type='info') {
  const el = document.getElementById('toast');
  if (!el) return;
  const bg = {info:'#1e293b',ok:'#065f46',error:'#991b1b',warn:'#92400e'};
  el.style.background = bg[type]||bg.info;
  el.style.color = '#e2e8f0';
  el.textContent = msg;
  el.className = 'show';
  clearTimeout(el._hide);
  el._hide = setTimeout(() => el.className='', 4000);
}

function setCardStatus(cardId, ok) {
  const card = document.getElementById(cardId)?.closest('.card');
  if (!card) return;
  card.classList.remove('card-ok','card-error');
  if (ok === true) card.classList.add('card-ok');
  else if (ok === false) card.classList.add('card-error');
}

function updateIncidentFields() {
  const sel = document.getElementById('api-select');
  if (!sel.value) return;
  const [service, env] = sel.value.split('|');
  document.getElementById('inc-name').value = service + ' — ' + env + ' ' + randomFailure();
  document.getElementById('inc-desc').value = randomDesc();
  document.getElementById('inc-tags').value = 'service:' + service + ',env:' + env + ',team:observai,purpose:incident';
}

function randomFailure() {
  const f = ['deploy failure','resource starvation','latency spike','dependency outage','data corruption'];
  return f[Math.floor(Math.random() * f.length)];
}

function randomDesc() {
  const d = ['Error rate exceeded threshold','CPU usage above 90%','Memory usage critical','Request latency spike','Connection pool exhausted','Disk I/O saturation','Certificate expired'];
  return d[Math.floor(Math.random() * d.length)];
}

async function createSandbox() {
  const btn = document.getElementById('sandbox-btn');
  const out = document.getElementById('sandbox-out');
  const results = document.getElementById('sandbox-results');
  btn.disabled = true;
  out.textContent = '⏳ Creating sandbox monitors...';
  results.classList.add('hidden');
  log('Sandbox: creating monitors...', 'info');
  try {
    const r = await fetch('/sandbox/create', {method:'POST'});
    const data = await r.json();
    console.log('[sandbox] Response:', data);
    if (data.status === 'ok') {
      currentSession = data.session || '';
      const mon = data.monitors || [];
      const total = mon.length;
      const ok = mon.filter(m => m.status === 'created' || m.status === 'exists' || m.status === 'ok').length;
      out.textContent = '✅ ' + ok + '/' + total + ' monitors ready';
      results.classList.remove('hidden');
      results.innerHTML = mon.map(m =>
        '<div class="flex items-center gap-2"><span class="' +
        (m.status === 'created' || m.status === 'exists' || m.status === 'ok' ? 'monitor-ok' : 'monitor-error') +
        '">' + (m.status === 'created' || m.status === 'exists' || m.status === 'ok' ? '✓' : '✗') +
        '</span> <span class="text-slate-300">' + m.service + '</span> ' +
        '<span class="badge ' + (m.env === 'prd' ? 'bg-orange-500/20 text-orange-400' : 'bg-blue-500/20 text-blue-400') +
        '">' + m.env + '</span> <span class="text-slate-500">' + m.monitor + '</span>' +
        (m.status === 'exists' ? ' <span class="text-xs text-slate-600">(already exists)</span>' : '') +
        '</div>'
      ).join('');
      const d = data.duplicates || 0;
      const newCreated = data.created || 0;
      const sloCreated = data.slos_created || 0;
      const sloErr = data.slo_errors || 0;
      let sloStr = '';
      if (sloCreated) sloStr = ', ' + sloCreated + ' SLOs' + (sloErr ? ' (' + sloErr + ' errors)' : '');
      const suffix = newCreated > 0 ? ' (' + newCreated + ' new)' : d > 0 ? ' (all existed)' : '';
      out.textContent = '✅ ' + ok + '/' + total + ' monitors' + sloStr;
      toast('Sandbox: ' + ok + '/' + total + ' monitors' + sloStr + suffix, ok === total && !sloErr ? 'ok' : 'warn');
      log('Sandbox: ' + ok + '/' + total + ' monitors ready' + suffix, ok === total ? 'ok' : 'warn');
      if (currentSession) {
        const sessEl = document.getElementById('sandbox-session');
        sessEl.classList.remove('hidden');
        sessEl.innerHTML = 'Session: <code class="text-brand-400">' + currentSession + '</code> &middot; filter in Datadog with <code>sandbox_session:' + currentSession + '</code>';
      }
      setCardStatus('sandbox-btn', ok === total);
    } else {
      out.textContent = '⚠️ Error: ' + (data.error || 'unknown');
      log('Sandbox error: ' + (data.error || JSON.stringify(data)), 'error');
      toast('Sandbox failed: ' + (data.error || 'unknown'), 'error');
    }
  } catch(e) {
    out.textContent = '⚠️ Request failed: ' + e.message;
    log('Sandbox request error: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

async function cleanupSandbox() {
  const btn = document.getElementById('cleanup-btn');
  const out = document.getElementById('sandbox-out');
  const results = document.getElementById('sandbox-results');
  if (!confirm('Resolve ALL sandbox incidents and delete ALL sandbox monitors/SLOs from Datadog? This cannot be undone.')) return;
  btn.disabled = true;
  out.textContent = '⏳ Cleaning up monitors and incidents...';
  results.classList.add('hidden');
  log('Sandbox: cleaning up monitors and incidents...', 'warn');
  try {
    const r = await fetch('/sandbox/cleanup', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({session: currentSession})});
    const data = await r.json();
    console.log('[cleanup] Response:', data);
    if (data.status === 'ok') {
      document.getElementById('sandbox-session').classList.add('hidden');
      out.textContent = '🗑️ ' + data.deleted + ' monitors deleted' + (data.resolved ? ', ' + data.resolved + ' incidents resolved' : '') + (data.slos_deleted ? ', ' + data.slos_deleted + ' SLOs deleted' : '') + (data.errors ? ', ' + data.errors + ' errors' : '');
      toast('Cleanup: ' + data.deleted + ' monitors, ' + data.resolved + ' incidents' + (data.slos_deleted ? ', ' + data.slos_deleted + ' SLOs' : ''), 'ok');
      log('Cleanup: ' + data.deleted + ' monitors deleted, ' + data.resolved + ' incidents resolved' + (data.slos_deleted ? ', ' + data.slos_deleted + ' SLOs deleted' : ''), data.errors ? 'warn' : 'ok');
    } else {
      out.textContent = '⚠️ Cleanup error: ' + (data.error || 'unknown');
      log('Cleanup error: ' + (data.error || JSON.stringify(data)), 'error');
    }
  } catch(e) {
    out.textContent = '⚠️ Cleanup failed: ' + e.message;
    log('Cleanup request error: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

async function runSeed() {
  const out = document.getElementById('inc-out');
  const sel = document.getElementById('api-select');
  out.textContent = '⏳ Sending...';
  log('Creating incidents...', 'info');
  try {
    // Step 1: Take service down before incident
    const downDuration = parseInt(document.getElementById('down-duration').value);
    if (downDuration > 0 && sel.value) {
      const [service, env] = sel.value.split('|');
      out.textContent = '⏳ Taking ' + service + ' (' + env + ') down for ' + downDuration + 's...';
      log('Taking ' + service + ' (' + env + ') down...', 'warn');
      try {
        const dr = await fetch('/api/down', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({service, env, duration: downDuration})});
        const dd = await dr.json();
        if (dd.status === 'ok') {
          log('Service down: ' + JSON.stringify(dd.response), 'warn');
          await new Promise(r => setTimeout(r, 2000));
        } else {
          log('Service down failed: ' + (dd.error || ''), 'error');
        }
      } catch(e) {
        log('Service down request error: ' + e.message, 'error');
      }
    }
    // Step 2: Create incidents
    const rawName = document.getElementById('inc-name').value || 'API Incident';
    const rawTags = document.getElementById('inc-tags').value || '';
    const body = {
      quantity: parseInt(document.getElementById('inc-qty').value),
      interval_seconds: parseInt(document.getElementById('inc-int').value),
      name: rawName,
      description: document.getElementById('inc-desc').value || '',
      tags: rawTags,
      severity: document.getElementById('inc-sev').value,
      evidence: document.getElementById('inc-evidence').checked,
      session: currentSession,
    };
    if (sel.value) {
      const [service, env] = sel.value.split('|');
      body.service = service;
      body.env = env;
    }
    console.log('[seed] incidents body:', JSON.stringify(body));
    const r = await fetch('/seed/incidents', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    const data = await r.json();
    console.log('[seed] response:', data);
    if (data.status === 'ok') {
      const ic = data.incident || data.counts || {};
      const ev = data.evidence || {};
      const inc = ic.incidents || 0;
      const sent = ic.sent || 0;
      const errs = ic.errors || 0;
      let evParts = [];
      if (inc) evParts.push(inc + ' incidents');
      if (ev.logs) evParts.push(ev.logs + ' logs');
      if (ev.events) evParts.push(ev.events + ' events');
      if (ev.metrics) evParts.push(ev.metrics + ' metrics');
      if (ev.monitors) evParts.push(ev.monitors + ' monitors');
      const evStr = evParts.length ? ' + ' + evParts.join(', ') : '';
      const summary = inc + ' incidents' + (errs ? ', ' + errs + ' errors' : '') + evStr;
      out.textContent = '✅ ' + summary;
      toast('Incidents: ' + summary, 'ok');
      log('Incidents OK — ' + summary, 'ok');
      setCardStatus('inc-out', true);
      // Verify in background
      try {
        await new Promise(r => setTimeout(r, 2000));
        const vr = await fetch('/verify/events', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({title: rawName, expected: sent, mins_back: 5})});
        const vd = await vr.json();
        if (vd.status === 'ok') {
          out.textContent = '✅ ' + summary + ' — ✅ ' + vd.found + ' confirmed';
          log('Verify: ' + vd.found + ' events confirmed in Datadog', 'ok');
        } else if (vd.status === 'partial') {
          out.textContent = '✅ ' + summary + ' ⚡ (verifying...)';
          log('Verify: ' + vd.found + '/' + vd.expected + ' found so far', 'info');
        }
      } catch(ve) {
        log('Verify skipped: ' + ve.message, 'warn');
      }
    } else {
      out.textContent = '⚠️ Error: ' + (data.error || 'unknown');
      log('Incidents error: ' + (data.error || JSON.stringify(data)), 'error');
    }
  } catch(e) {
    out.textContent = '⚠️ Request failed: ' + e.message;
    log('Incidents request error: ' + e.message, 'error');
  }
}

// Init API dropdown
(async function() {
  try {
    const r = await fetch('/sandbox/apis');
    const data = await r.json();
    const sel = document.getElementById('api-select');
    sel.innerHTML = '<option value="">Select an API service...</option>' +
      (data.apis || []).map(a =>
        '<option value="' + a.service + '|' + a.env + '">' + a.label + '</option>'
      ).join('');
    API_LIST.push(...(data.apis || []));
    if (data.apis && data.apis.length > 0) {
      sel.value = data.apis[0].service + '|' + data.apis[0].env;
      updateIncidentFields();
    }
  } catch(e) {
    console.error('[init] Failed to load APIs:', e);
  }
})();
</script>
</body>
</html>"""


@app.get("/")
async def index():
    return HTMLResponse(HTML)


# ── Sandbox endpoints ──────────────────────────────────────────


@app.get("/sandbox/apis")
async def sandbox_apis():
    return {"apis": _sandbox_api_list()}


@app.post("/sandbox/create")
async def sandbox_create(body: dict[str, Any] = {}):
    if not DD_APP_KEY:
        return {"status": "error", "error": "DD_APP_KEY required to create monitors"}
    session = _new_session()
    created = []
    errors = 0
    duplicates = 0
    health_monitor_ids = {}
    async with httpx.AsyncClient(timeout=15) as c:
        headers = _dd_headers()
        await _delete_sandbox_infra(c, headers)
        for api_svc in API_SERVICES:
            svc = api_svc["name"]
            env = api_svc["env"]
            tags = _tag_list(svc, env)
            if _session_tag():
                tags = tags + [_session_tag()]
            for mon in SANDBOX_MONITORS:
                try:
                    metric_svc = _metric_prefix(svc)
                    query = mon["query_tpl"].format(metric_svc=metric_svc, service=svc, env=env)
                    message = mon["message_tpl"].format(service=svc, env=env)
                    mon_name = f"[Sandbox] {svc} — {mon['name']} ({env})"
                    r = await c.post(
                        f"{DD_API_BASE}/api/v1/monitor",
                        headers=headers,
                        json={
                            "name": mon_name,
                            "type": mon["type"],
                            "query": query,
                            "message": message,
                            "tags": tags,
                            "options": {"thresholds": mon["thresholds"], "notify_no_data": False},
                        },
                    )
                    body = r.json()
                    if r.status_code in (200, 201):
                        created.append(
                            {
                                "service": svc,
                                "env": env,
                                "monitor": mon["name"],
                                "status": "created",
                                "id": body.get("id"),
                            }
                        )
                        if mon["id"] == "health":
                            health_monitor_ids[f"{svc}|{env}"] = body.get("id")
                    elif (
                        "duplicate"
                        in (
                            body.get("errors", [""])[0]
                            if isinstance(body.get("errors"), list)
                            else str(body.get("errors", ""))
                        ).lower()
                    ):
                        duplicates += 1
                        err_str = (
                            body.get("errors", [""])[0]
                            if isinstance(body.get("errors"), list)
                            else str(body.get("errors", ""))
                        )
                        dup_id = (
                            err_str.split("monitor_id:")[-1].split()[0]
                            if "monitor_id:" in err_str
                            else None
                        )
                        if dup_id and dup_id.isdigit():
                            dup_id = int(dup_id)
                        # Ensure the reused monitor carries the session tag for scoping.
                        if dup_id and _session_tag():
                            try:
                                await c.patch(
                                    f"{DD_API_BASE}/api/v1/monitor/{dup_id}",
                                    headers=headers,
                                    json={"tags": tags},
                                )
                            except Exception:
                                pass
                        created.append(
                            {
                                "service": svc,
                                "env": env,
                                "monitor": mon["name"],
                                "status": "exists",
                                "id": dup_id,
                            }
                        )
                        if mon["id"] == "health":
                            health_monitor_ids[f"{svc}|{env}"] = dup_id
                    else:
                        errors += 1
                        created.append(
                            {
                                "service": svc,
                                "env": env,
                                "monitor": mon["name"],
                                "status": "error",
                                "detail": r.text[:120],
                            }
                        )
                except Exception as e:
                    errors += 1
                    created.append(
                        {
                            "service": svc,
                            "env": env,
                            "monitor": mon["name"],
                            "status": "error",
                            "detail": str(e),
                        }
                    )
                await asyncio.sleep(0.3)
        # ── Create monitor-based SLOs (availability) ──
        slos = 0
        slo_errors = 0
        for api_svc in API_SERVICES:
            svc = api_svc["name"]
            env = api_svc["env"]
            mon_id = health_monitor_ids.get(f"{svc}|{env}")
            if not mon_id:
                slo_errors += 1
                continue
            try:
                slo_name = f"[Sandbox] {svc} ({env}) - Availability"
                slo_payload = {
                    "type": "monitor",
                    "name": slo_name,
                    "description": f"Availability SLO for {svc} in {env} environment",
                    "thresholds": [{"target": 99.0, "timeframe": "7d", "warning": 99.5}],
                    "monitor_ids": [mon_id],
                    "tags": [f"service:{svc}", f"env:{env}", "team:observai", "purpose:sandbox"]
                    + ([_session_tag()] if _session_tag() else []),
                }
                r = await c.post(
                    f"{DD_API_BASE}/api/v1/slo",
                    headers=headers,
                    json=slo_payload,
                )
                if r.status_code in (200, 201):
                    slos += 1
                else:
                    slo_errors += 1
            except Exception:
                slo_errors += 1
            await asyncio.sleep(0.2)
    return {
        "status": "ok" if errors == 0 and slo_errors == 0 else "partial",
        "session": session,
        "total": len(created),
        "created": len(created) - errors - duplicates,
        "duplicates": duplicates,
        "errors": errors,
        "monitors": created,
        "slos_created": slos,
        "slo_errors": slo_errors,
    }


@app.post("/sandbox/cleanup")
async def sandbox_cleanup(body: dict[str, Any] = {}):
    if not DD_APP_KEY:
        return {"status": "error", "error": "DD_APP_KEY required"}
    session = body.get("session", "") or ""
    deleted = 0
    errors = 0
    resolved = 0
    deleted_slos = 0
    async with httpx.AsyncClient(timeout=60) as c:
        headers = _dd_headers()
        # ── 1. Delete sandbox SLOs (must precede monitors: a monitor linked to an SLO cannot be deleted) ──
        try:
            r = await c.get(
                f"{DD_API_BASE}/api/v1/slo?query=%5BSandbox%5D",
                headers=headers,
            )
            if r.status_code == 200:
                body = r.json()
                slo_list = body.get("data", [])
                if isinstance(slo_list, dict):
                    slo_list = [slo_list]
                for slo in slo_list:
                    slo_id = slo.get("id") if isinstance(slo, dict) else None
                    if not slo_id:
                        continue
                    if await _dd_delete(c, f"{DD_API_BASE}/api/v1/slo/{slo_id}", headers):
                        deleted_slos += 1
                    else:
                        errors += 1
                    await asyncio.sleep(0.1)
        except Exception:
            errors += 1

        # ── 3. Resolve sandbox incidents ──
        try:
            # Incident search by session is unreliable via API; resolve all [Sandbox] incidents.
            inc_query = "Sandbox"
            offset = 0
            while True:
                r = await c.get(
                    f"{DD_API_BASE}/api/v2/incidents?page%5Bsize%5D=100&page%5Boffset%5D={offset}&filter%5Bquery%5D={inc_query}",
                    headers=headers,
                )
                if r.status_code != 200:
                    errors += 1
                    break
                body = r.json()
                items = body.get("data", [])
                if not items:
                    break
                for item in items:
                    inc_id = item.get("id")
                    if not inc_id:
                        continue
                    try:
                        pr = await c.patch(
                            f"{DD_API_BASE}/api/v2/incidents/{inc_id}",
                            headers=headers,
                            json={
                                "data": {
                                    "type": "incidents",
                                    "id": inc_id,
                                    "attributes": {
                                        "fields": {
                                            "state": {"value": "resolved"},
                                            "severity": {"value": "SEV-5"},
                                        },
                                    },
                                }
                            },
                        )
                        if pr.status_code in (200, 201, 204):
                            resolved += 1
                        else:
                            errors += 1
                    except Exception:
                        errors += 1
                    await asyncio.sleep(0.1)
                offset = (
                    (body.get("meta") or {}).get("pagination", {}).get("next_offset", offset + 100)
                )
        except Exception:
            errors += 1

        # ── 2. Delete sandbox monitors (after SLOs so health monitors are no longer SLO-linked) ──
        try:
            r = await c.get(f"{DD_API_BASE}/api/v1/monitor", headers=headers)
            if r.status_code != 200:
                return {"status": "error", "error": f"Failed to list monitors: {r.text[:200]}"}
            monitors = r.json()
            sandbox_mons = [m for m in monitors if m.get("name", "").startswith("[Sandbox]")]
            for mon in sandbox_mons:
                mon_id = mon.get("id")
                if not mon_id:
                    continue
                if await _dd_delete(c, f"{DD_API_BASE}/api/v1/monitor/{mon_id}", headers):
                    deleted += 1
                else:
                    errors += 1
                await asyncio.sleep(0.1)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    return {
        "status": "ok",
        "deleted": deleted,
        "resolved": resolved,
        "slos_deleted": deleted_slos,
        "errors": errors,
        "total_found": deleted + errors,
    }


# ── Service Down simulation ─────────────────────────────────────


SERVICE_HOST_MAP = {
    ("api-gateway", "demo"): "api-gateway:8002",
    ("api-gateway", "dev"): "api-gateway-dev:8002",
    ("api-gateway", "prd"): "api-gateway-prd:8002",
    ("user-service", "demo"): "user-service:8001",
    ("user-service", "dev"): "user-service-dev:8001",
    ("user-service", "prd"): "user-service-prd:8001",
}


@app.post("/api/down")
async def api_down(body: dict[str, Any]):
    service = body.get("service", "")
    env = body.get("env", "")
    duration = body.get("duration", 10)
    host = SERVICE_HOST_MAP.get((service, env))
    if not host:
        return {"status": "error", "error": f"Unknown service/env: {service}/{env}"}
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.post(f"http://{host}/down", json={"duration": duration})
            data = r.json()
        return {
            "status": "ok",
            "response": data,
            "service": service,
            "env": env,
            "duration": duration,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "service": service, "env": env}


# ── Helper functions ────────────────────────────────────────────


async def _send_dd_log(
    service: str,
    message: str,
    level: str = "info",
    extra_tags: str = "",
    source: str = "demo-ui",
    timestamp: int | None = None,
    env: str = "demo",
) -> int:
    try:
        dd_tags = f"service:{service},env:{env},team:observai,purpose:demo"
        if CURRENT_SANDBOX_SESSION:
            dd_tags += f",sandbox_session:{CURRENT_SANDBOX_SESSION}"
        if extra_tags:
            dd_tags += "," + ",".join(t.strip() for t in extra_tags.split(",") if t.strip())
        ts = timestamp or int(time.time() * 1000)
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.post(
                f"{DD_LOG_INTAKE}/api/v2/logs",
                headers=_dd_headers(),
                json=[
                    {
                        "ddsource": source,
                        "ddtags": dd_tags,
                        "hostname": service,
                        "service": service,
                        "message": message,
                        "status": level,
                        "timestamp": ts,
                    }
                ],
            )
            return r.status_code
    except Exception:
        return 0


async def _send_dd_event(
    service: str, title: str, text: str, alert_type: str = "info", tags: str = "", env: str = "demo"
) -> int:
    try:
        dd_tags = [f"service:{service}", f"env:{env}", "team:observai", "purpose:demo"]
        if tags:
            dd_tags += [t.strip() for t in tags.split(",") if t.strip()]
        if CURRENT_SANDBOX_SESSION:
            dd_tags.append(f"sandbox_session:{CURRENT_SANDBOX_SESSION}")
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.post(
                f"{DD_API_BASE}/api/v1/events",
                headers=_dd_headers(),
                json={
                    "title": title,
                    "text": text,
                    "alert_type": alert_type,
                    "tags": dd_tags,
                    "host": service,
                    "date_happened": int(time.time()),
                },
            )
            return r.status_code
    except Exception:
        return 0


INTERVAL_OPTIONS = [1, 5, 15, 20]


def _resolve_interval(interval_seconds: int) -> float:
    if interval_seconds < 0:
        return float(random.choice(INTERVAL_OPTIONS))
    return float(interval_seconds)


# ── Seed: Incidents (using sandbox APIs) ───────────────────────


@app.post("/seed/incidents")
async def seed_incidents(body: dict[str, Any]):
    qty = min(body.get("quantity", 1), 10)
    severity = body.get("severity", "SEV-3")
    name_prefix = body.get("name", "") or "API Incident"
    description = body.get("description", "") or random.choice(ERROR_MSGS)
    extra_tags = body.get("tags", "")
    interval = body.get("interval_seconds", 0)
    evidence = body.get("evidence", True)
    svc_override = body.get("service", "")
    env_override = body.get("env", "")
    # Scope incidents to the sandbox session (from /sandbox/create) so they're filterable.
    session = body.get("session") or CURRENT_SANDBOX_SESSION

    ev = {"logs": 0, "events": 0, "metrics": 0, "monitors": 0, "sent": 0, "errors": 0}

    async with httpx.AsyncClient(timeout=10) as c:
        dd_headers = _dd_headers()

        for i in range(qty):
            if svc_override:
                svc = svc_override
                env = env_override or "demo"
            else:
                svc = random.choice(API_SERVICES)["name"]
                env = random.choice(API_SERVICES)["env"]

            # Datadog incidents v2 ignore attributes.tags, so scope the run via the title.
            sess_part = f" {session} " if session else " "
            base_title = f"[Sandbox]{sess_part}{name_prefix} — {svc} ({env})"
            title = f"{base_title} — {random.choice(FAILURE_PATTERNS).replace('_', ' ')} failure"
            # Auto-severity based on environment
            effective_severity = severity
            if env == "prd":
                effective_severity = "SEV-1"
            elif env == "dev":
                effective_severity = "SEV-2"
            incident_tags = [f"service:{svc}", f"env:{env}", "team:observai", "purpose:incident"]
            if session:
                incident_tags.append(f"sandbox_session:{session}")
            if extra_tags:
                incident_tags += [t.strip() for t in extra_tags.split(",") if t.strip()]
            tag_str = ",".join(incident_tags)

            # 0. Real Datadog Incident (via v2 API)
            now_ms = int(time.time() * 1000)
            start_ms = now_ms - 600000  # last 10 min
            try:
                dd_ui_base = f"https://{DD_SITE}"
                logs_url = f"{dd_ui_base}/logs?query=service%3A{svc}%20env%3A{env}%20purpose%3Aincident&from_ts={start_ms}&to_ts={now_ms}&live=false"
                events_url = f"{dd_ui_base}/event/explorer?query=service%3A{svc}%20env%3A{env}%20purpose%3Aincident&from_ts={start_ms}&to_ts={now_ms}&live=false"
                impact_scope = f"{description[:80]} | Logs[{start_ms // 1000}-{now_ms // 1000}]: {logs_url} | Events: {events_url}"
                dd_payload = {
                    "data": {
                        "type": "incidents",
                        "attributes": {
                            "title": title,
                            "customer_impacted": True,
                            "customer_impact_scope": impact_scope[:200],
                            "fields": {
                                "severity": {"value": effective_severity},
                                "state": {"value": "active"},
                            },
                            "initial_cells": [
                                {
                                    "cell_type": "markdown",
                                    "content": {
                                        "content": f"**{title}**\n\n{description}\n\nTags: {tag_str}\n\n[View Logs]({logs_url}) | [View Events]({events_url})",
                                        "important": True,
                                    },
                                }
                            ],
                        },
                    }
                }
                r = await c.post(
                    f"{DD_API_BASE}/api/v2/incidents",
                    headers=dd_headers,
                    json=dd_payload,
                )
                if r.status_code in (200, 201, 202):
                    ev["incidents"] = ev.get("incidents", 0) + 1
                else:
                    ev["errors"] += 1
            except Exception:
                ev["errors"] += 1

            if evidence:
                # 1. Logs
                for _ in range(random.randint(2, 4)):
                    log_msg = random.choice(ERROR_MSGS)
                    log_status = random.choice(["error", "warn", "error", "info"])
                    log_ts = int(time.time() * 1000) - random.randint(0, 300000)
                    try:
                        r = await c.post(
                            f"{DD_LOG_INTAKE}/api/v2/logs",
                            headers=dd_headers,
                            json=[
                                {
                                    "ddsource": "incident-engine",
                                    "ddtags": tag_str,
                                    "hostname": svc,
                                    "service": svc,
                                    "message": f"{base_title} | {log_msg}",
                                    "status": log_status,
                                    "timestamp": log_ts,
                                }
                            ],
                        )
                        if str(r.status_code).startswith("2"):
                            ev["logs"] += 1
                    except Exception:
                        ev["errors"] += 1

                # 2. Events
                alert_map = {
                    "SEV-1": "error",
                    "SEV-2": "error",
                    "SEV-3": "warning",
                    "SEV-4": "warning",
                    "SEV-5": "info",
                }
                for _ in range(random.randint(1, 3)):
                    try:
                        r = await c.post(
                            f"{DD_API_BASE}/api/v1/events",
                            headers=dd_headers,
                            json={
                                "title": base_title,
                                "text": f"{description} | {random.choice(ERROR_MSGS)}",
                                "alert_type": alert_map.get(severity, "error"),
                                "tags": incident_tags,
                                "host": svc,
                                "date_happened": int(time.time()) - random.randint(0, 120),
                            },
                        )
                        if str(r.status_code).startswith("2"):
                            ev["events"] += 1
                    except Exception:
                        ev["errors"] += 1

                # 3. Metrics
                metric_base = random.choice(
                    ["system.cpu.user", "system.mem.used", "net.bytes_sent"]
                )
                for pt in range(3):
                    try:
                        val = (
                            round(random.uniform(50, 98), 1)
                            if pt < 2
                            else round(random.uniform(80, 99.9), 1)
                        )
                        r = await c.post(
                            f"{DD_API_BASE}/api/v2/series",
                            headers=dd_headers,
                            json={
                                "series": [
                                    {
                                        "metric": metric_base,
                                        "type": 0,
                                        "points": [
                                            {
                                                "timestamp": int(time.time()) - (3 - pt) * 30,
                                                "value": val,
                                            }
                                        ],
                                        "tags": incident_tags,
                                    }
                                ]
                            },
                        )
                        if str(r.status_code).startswith("2"):
                            ev["metrics"] += 1
                    except Exception:
                        ev["errors"] += 1

                # 4. Monitor
                if DD_APP_KEY:
                    try:
                        mon_name = f"{name_prefix[:40]} — {svc} {severity}"
                        r = await c.post(
                            f"{DD_API_BASE}/api/v1/monitor",
                            headers=dd_headers,
                            json={
                                "name": mon_name,
                                "type": "query alert",
                                "query": f"avg(last_5m):avg:{metric_base}{{service:{svc}}} > 90",
                                "message": f"{description} | Evidence monitor for {title}",
                                "tags": incident_tags,
                                "options": {"thresholds": {"critical": 90, "warning": 75}},
                            },
                        )
                        if r.status_code in (200, 201):
                            ev["monitors"] += 1
                    except Exception:
                        ev["errors"] += 1

            # 5. Main incident event
            msg = f"{description} | {random.choice(ERROR_MSGS)}"
            code = await _send_dd_event(svc, title, msg, "error", extra_tags, env)
            if str(code).startswith("2"):
                ev["sent"] += 1
            else:
                ev["errors"] += 1
            if interval and i < qty - 1:
                await asyncio.sleep(_resolve_interval(interval))

    await _send_dd_log(
        "demo", f'Seeded incident "{name_prefix}" ({severity}) with evidence', "info"
    )
    return {
        "status": "ok",
        "incident": {
            "sent": ev["sent"],
            "incidents": ev.get("incidents", 0),
            "errors": ev["errors"],
            "severity": severity,
            "name": name_prefix,
        },
        "evidence": {
            "logs": ev["logs"],
            "events": ev["events"],
            "metrics": ev["metrics"],
            "monitors": ev["monitors"],
        },
        "total": ev["logs"]
        + ev["events"]
        + ev["metrics"]
        + ev["monitors"]
        + ev["sent"]
        + ev.get("incidents", 0),
    }


# ── Verify ──────────────────────────────────────────────────────


@app.post("/verify/events")
async def verify_events(body: dict[str, Any]):
    title = body.get("title", "")
    expected = body.get("expected", 1)
    mins_back = body.get("mins_back", 5)
    try:
        end_ts = int(time.time())
        start_ts = int(time.time()) - mins_back * 60
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"{DD_API_BASE}/api/v1/events",
                headers=_dd_headers(),
                params={"start": start_ts, "end": end_ts},
            )
        if r.status_code != 200:
            return {
                "status": "error",
                "error": f"Datadog API returned {r.status_code}",
                "found": 0,
                "expected": expected,
            }
        events = r.json().get("events", [])
        matching = [
            e for e in events if title and title.split(" —")[0].strip() in e.get("title", "")
        ]
        found = len(matching)
        urls = []
        sample_titles = []
        for e in matching[:5]:
            eid = e.get("id")
            if eid:
                urls.append(f"https://{DD_SITE}/event/event?id={eid}")
            sample_titles.append(e.get("title", "")[:60])
        if found >= expected:
            return {
                "status": "ok",
                "found": found,
                "expected": expected,
                "urls": urls,
                "sample_titles": sample_titles,
            }
        elif found > 0:
            return {
                "status": "partial",
                "found": found,
                "expected": expected,
                "urls": urls,
                "sample_titles": sample_titles,
            }
        else:
            return {
                "status": "partial",
                "found": 0,
                "expected": expected,
                "urls": [],
                "sample_titles": [],
            }
    except Exception as e:
        return {"status": "error", "error": str(e), "found": 0, "expected": expected}


# ── Demo UI health ──────────────────────────────────────────────


@app.post("/seed/demo-ui-health")
async def seed_self_check():
    results = {"status": "ok", "checks": []}
    if DD_API_KEY:
        results["checks"].append({"name": "dd_api_key", "status": "ok"})
    else:
        results["checks"].append({"name": "dd_api_key", "status": "missing"})
        results["status"] = "degraded"
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{DD_API_BASE}/api/v1/validate", headers={"DD-API-KEY": DD_API_KEY})
        results["checks"].append(
            {
                "name": "dd_api_connect",
                "status": "ok" if r.status_code == 200 else "error",
                "code": r.status_code,
            }
        )
        if r.status_code != 200:
            results["status"] = "degraded"
    except Exception as e:
        results["checks"].append({"name": "dd_api_connect", "status": "error", "error": str(e)})
        results["status"] = "degraded"
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get("http://test-runner:8003/health")
        results["checks"].append(
            {"name": "test_runner", "status": "ok" if r.status_code == 200 else "error"}
        )
        if r.status_code != 200:
            results["status"] = "degraded"
    except Exception as e:
        results["checks"].append({"name": "test_runner", "status": "unreachable", "error": str(e)})
        results["status"] = "degraded"
    return results


@app.get("/test-datadog-connection")
async def test_datadog_connection():
    results: dict[str, Any] = {"status": "ok", "checks": []}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{DD_API_BASE}/api/v1/monitor", headers=_dd_headers())
        n_monitors = len(r.json()) if r.status_code == 200 else 0
        results["checks"].append(
            {
                "name": "monitors",
                "status": "ok" if r.status_code == 200 else "error",
                "total": n_monitors,
                "code": r.status_code,
            }
        )
    except Exception as e:
        results["checks"].append({"name": "monitors", "status": "error", "error": str(e)})
        results["status"] = "degraded"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"{DD_API_BASE}/api/v2/logs/events/search",
                headers={"DD-API-KEY": DD_API_KEY, "Content-Type": "application/json"},
                json={"filter": {"from": "now-2h", "to": "now"}, "limit": 5},
            )
        data = r.json() if r.status_code == 200 else {}
        n_logs = len(data.get("data", [])) if r.status_code == 200 else 0
        results["checks"].append(
            {
                "name": "logs_search",
                "status": "ok" if r.status_code == 200 else "error",
                "hits": n_logs,
                "code": r.status_code,
            }
        )
    except Exception as e:
        results["checks"].append({"name": "logs_search", "status": "error", "error": str(e)})
        results["status"] = "degraded"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{DD_API_BASE}/api/v1/slo", headers=_dd_headers())
        n_slos = len(r.json().get("data", [])) if r.status_code == 200 else 0
        results["checks"].append(
            {
                "name": "slos",
                "status": "ok" if r.status_code == 200 else "error",
                "total": n_slos,
                "code": r.status_code,
            }
        )
    except Exception as e:
        results["checks"].append({"name": "slos", "status": "error", "error": str(e)})
        results["status"] = "degraded"
    return results


@app.get("/smoke-test")
async def smoke_test():
    results: dict[str, Any] = {"status": "ok", "tests": []}
    for svc_name, port in [
        ("user-service", 8001),
        ("user-service-dev", 8001),
        ("user-service-prd", 8001),
        ("api-gateway", 8002),
        ("api-gateway-dev", 8002),
        ("api-gateway-prd", 8002),
        ("test-runner", 8003),
    ]:
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(f"http://{svc_name}:{port}/health")
            ok = r.status_code == 200
        except Exception:
            ok = False
        results["tests"].append({"service": svc_name, "status": "ok" if ok else "error"})
        if not ok:
            results["status"] = "degraded"
    return results


# ── Debug ───────────────────────────────────────────────────────


@app.get("/debug/send-event")
async def debug_send_event():
    url = f"{DD_API_BASE}/api/v1/events"
    headers = _dd_headers()
    payload = {
        "title": "[tests][demo] DEBUG TEST — delete me",
        "text": "Debug test from demo-ui — if you see this, events work",
        "alert_type": "info",
        "tags": "service:demo-ui,env:demo,purpose:debug",
        "date_happened": int(time.time()),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(url, headers=headers, json=payload)
        return {
            "status_code": r.status_code,
            "response": r.text[:500] if r.text else "(empty)",
            "api_key_present": bool(DD_API_KEY),
            "api_key_preview": DD_API_KEY[:8] + "..." if DD_API_KEY else "NONE",
            "app_key_present": bool(DD_APP_KEY),
        }
    except Exception as e:
        return {"status_code": 0, "error": str(e)}
