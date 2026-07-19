const $ = (sel, el = document) => el.querySelector(sel);

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.json();
}

let selectedId = null;

async function boot() {
  const health = await api("/api/health");
  $("#modeBadge").textContent = `mode: ${health.mode}`;
  await Promise.all([refreshMetrics(), refreshSamples(), refreshCases(), maybeEval()]);
  $("#fileInput").addEventListener("change", onUpload);
  $("#btnEval").addEventListener("click", async () => {
    $("#btnEval").disabled = true;
    try {
      await maybeEval(true);
    } finally {
      $("#btnEval").disabled = false;
    }
  });
}

async function refreshMetrics() {
  const m = await api("/api/cases/metrics/summary");
  $("#mTotal").textContent = m.total_cases;
  $("#mAuto").textContent = m.auto_resolved;
  $("#mReview").textContent = m.needs_review;
  $("#mRate").textContent = pct(m.auto_resolve_rate);
  $("#mConf").textContent = pct(m.avg_confidence);
}

async function maybeEval(force = false) {
  try {
    const e = await api("/api/evals/run");
    $("#mEval").textContent = pct(e.field_accuracy);
    if (force) alert(`Gold eval: ${e.cases} cases\nField accuracy: ${pct(e.field_accuracy)}\nTotal match: ${pct(e.total_match_rate)}\nVendor match: ${pct(e.vendor_match_rate)}`);
  } catch {
    $("#mEval").textContent = "n/a";
  }
}

async function refreshSamples() {
  const samples = await api("/api/samples");
  const box = $("#samples");
  box.innerHTML = "";
  for (const name of samples) {
    const btn = document.createElement("button");
    btn.className = "item";
    btn.innerHTML = `<div class="title">${name}</div><div class="meta">run sample</div>`;
    btn.onclick = () => runSample(name);
    box.appendChild(btn);
  }
}

async function refreshCases() {
  const cases = await api("/api/cases");
  const box = $("#caseList");
  box.innerHTML = "";
  for (const c of cases) {
    const btn = document.createElement("button");
    btn.className = "item" + (c.id === selectedId ? " active" : "");
    btn.innerHTML = `
      <div class="title">${escapeHtml(c.vendor_name || c.filename)}</div>
      <div class="meta">
        <span class="status ${c.status}">${c.status}</span>
        <span>${c.total != null ? money(c.total) : ""}</span>
        <span>${c.overall_confidence != null ? pct(c.overall_confidence) : ""}</span>
      </div>`;
    btn.onclick = () => selectCase(c.id);
    box.appendChild(btn);
  }
}

async function runSample(name) {
  const created = await api(`/api/cases/from-sample/${encodeURIComponent(name)}`, { method: "POST" });
  selectedId = created.id;
  await Promise.all([refreshCases(), refreshMetrics(), selectCase(created.id)]);
}

async function onUpload(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch("/api/cases", { method: "POST", body: fd });
  if (!res.ok) {
    alert(await res.text());
    return;
  }
  const created = await res.json();
  selectedId = created.id;
  e.target.value = "";
  await Promise.all([refreshCases(), refreshMetrics(), selectCase(created.id)]);
}

async function selectCase(id) {
  selectedId = id;
  await refreshCases();
  const c = await api(`/api/cases/${id}`);
  const root = $("#detail");
  const ext = c.extraction || {};
  const steps = c.steps || [];
  const validation = c.validation || {};
  const needsReview = c.status === "needs_review";

  root.innerHTML = `
    <div class="detail-head">
      <div>
        <h2>${escapeHtml(ext.vendor_name || c.filename)}</h2>
        <div class="meta">
          <span class="status ${c.status}">${c.status}</span>
          ${c.decision ? `<span class="badge muted">${c.decision}</span>` : ""}
          ${c.erp_bill_id ? `<span class="badge">ERP ${escapeHtml(c.erp_bill_id)}</span>` : ""}
        </div>
      </div>
      <div class="badge muted">${escapeHtml(c.filename)}</div>
    </div>

    <div class="kv">
      <div class="card"><div class="l">Invoice #</div><div class="v">${escapeHtml(ext.invoice_number || "—")}</div></div>
      <div class="card"><div class="l">Total</div><div class="v">${ext.total != null ? money(ext.total) : "—"} ${escapeHtml(ext.currency || "")}</div></div>
      <div class="card"><div class="l">Confidence</div><div class="v">${c.overall_confidence != null ? pct(c.overall_confidence) : "—"}</div></div>
      <div class="card"><div class="l">Date</div><div class="v">${escapeHtml(ext.invoice_date || "—")}</div></div>
    </div>

    <h3 class="sub">Agent timeline</h3>
    <div class="timeline">
      ${steps.map(s => `
        <div class="step ${s.status}">
          <div class="name">${escapeHtml(s.name)}</div>
          <div>
            <div><span class="status ${s.status}">${s.status}</span></div>
            <div class="detail">${escapeHtml(s.detail || "")}</div>
          </div>
        </div>`).join("")}
    </div>

    <h3 class="sub">Validation</h3>
    <div class="kv">
      <div class="card"><div class="l">OK</div><div class="v">${validation.ok ? "yes" : "no"}</div></div>
      <div class="card"><div class="l">Math</div><div class="v">${validation.math_ok ? "ok" : "fail"}</div></div>
      <div class="card"><div class="l">Policy</div><div class="v">${validation.policy_ok ? "ok" : "flagged"}</div></div>
    </div>
    ${(validation.issues || []).length ? `<pre class="audit">${escapeHtml((validation.issues || []).join("\n"))}</pre>` : ""}

    ${needsReview ? `
      <div class="review-box">
        <h3>Human-in-the-loop required</h3>
        <p class="detail">${escapeHtml(c.progress_ledger?.human_reason || "Review required before ERP writeback.")}</p>
        <label class="sub">Note</label>
        <input type="text" id="reviewNote" placeholder="Optional note" />
        <div class="review-actions">
          <button class="btn" id="btnApprove">Approve → create ERP bill</button>
          <button class="btn secondary" id="btnReject">Reject</button>
        </div>
      </div>` : ""}

    <h3 class="sub">Audit log</h3>
    <pre class="audit">${escapeHtml(JSON.stringify(c.audit || [], null, 2))}</pre>

    <h3 class="sub">Task ledger</h3>
    <pre class="audit">${escapeHtml(JSON.stringify(c.task_ledger || {}, null, 2))}</pre>
  `;

  if (needsReview) {
    $("#btnApprove").onclick = () => review(id, "approve");
    $("#btnReject").onclick = () => review(id, "reject");
  }
}

async function review(id, action) {
  const note = $("#reviewNote")?.value || "";
  await api(`/api/cases/${id}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, note }),
  });
  await Promise.all([refreshCases(), refreshMetrics(), selectCase(id)]);
}

function pct(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${Math.round(n * 1000) / 10}%`;
}
function money(n) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(n);
}
function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

boot().catch((e) => {
  console.error(e);
  $("#detail").innerHTML = `<div class="empty"><h2>API error</h2><p>${escapeHtml(e.message)}</p></div>`;
});
