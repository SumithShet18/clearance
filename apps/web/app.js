const $ = (sel, el = document) => el.querySelector(sel);

let selectedId = null;
let filterStatus = "needs_review";
let filterQ = "";
let demoMode = true;
let authRequired = false;

async function api(path, opts = {}) {
  const res = await fetch(path, {
    credentials: "include",
    ...opts,
    headers: {
      ...(opts.body && !(opts.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...(opts.headers || {}),
    },
  });
  if (res.status === 401) {
    showLogin(true);
    throw new Error("Authentication required");
  }
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res;
}

function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.add("hidden"), 3200);
}

function showLogin(on) {
  $("#loginGate").classList.toggle("hidden", !on);
  $("#appRoot").classList.toggle("hidden", on);
}

function showView(name) {
  $("#viewInbox").classList.toggle("hidden", name !== "inbox");
  $("#viewBills").classList.toggle("hidden", name !== "bills");
  $("#viewSettings").classList.toggle("hidden", name !== "settings");
}

let _booted = false;

async function boot() {
  // /api/auth/me is public — tells us if password mode is on and if cookie is valid
  const me = await fetch("/api/auth/me", { credentials: "include" }).then((r) => r.json());
  authRequired = !!me.auth_required;
  demoMode = true;

  const status = await fetch("/api/auth/status", { credentials: "include" }).then((r) =>
    r.json()
  );
  demoMode = !!status.demo_mode;

  // Open access (no CLEARANCE_PASSWORD): no login screen, no logout
  if (!authRequired) {
    showLogin(false);
    $("#btnLogout").classList.add("hidden");
    const badge = $("#modeBadge");
    if (badge && !badge.dataset.authNote) {
      badge.dataset.authNote = "1";
    }
    await finishBoot("open");
    return;
  }

  // Password required: show login until session cookie is valid
  if (!me.logged_in) {
    showLogin(true);
    $("#btnLogout").classList.add("hidden");
    $("#loginHint").textContent = "Enter the workspace password (CLEARANCE_PASSWORD).";
    wireLoginOnce();
    return;
  }

  showLogin(false);
  $("#btnLogout").classList.remove("hidden");
  await finishBoot("password");
}

async function finishBoot(authMode) {
  const health = await api("/api/health");
  $("#modeBadge").textContent =
    authMode === "open" ? `mode: ${health.mode} · open access` : `mode: ${health.mode} · signed in`;
  if (health.version) $("#verBadge").textContent = `v${health.version}`;

  if (demoMode) {
    $("#btnSeed").classList.remove("hidden");
    $("#btnEval").classList.remove("hidden");
    $("#btnBench").classList.remove("hidden");
    $("#footerDemo").classList.remove("hidden");
    $("#samplesHead").classList.remove("hidden");
  }

  if (!_booted) {
    _booted = true;
    $("#fileInput").addEventListener("change", onUpload);
    $("#btnSeed").addEventListener("click", seedDemo);
    $("#btnEval").addEventListener("click", runEval);
    $("#btnBench").addEventListener("click", runBench);
    $("#btnExportBills").addEventListener("click", exportBillsCsv);
    $("#btnExportBills2").addEventListener("click", exportBillsCsv);
    $("#btnNavInbox").addEventListener("click", () => {
      showView("inbox");
      refreshCases();
    });
    $("#btnNavBills").addEventListener("click", () => {
      showView("bills");
      loadBills();
    });
    $("#btnNavSettings").addEventListener("click", () => {
      showView("settings");
      loadSettings();
    });
    $("#btnSaveSettings").addEventListener("click", saveSettings);
    $("#btnLogout").addEventListener("click", doLogout);
    $("#caseSearch").addEventListener("input", (e) => {
      filterQ = e.target.value.trim();
      refreshCases();
    });
    document.querySelectorAll("#statusTabs .tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll("#statusTabs .tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        filterStatus = tab.dataset.status || "";
        refreshCases();
      });
    });
  }

  wireLoginOnce();
  await Promise.all([refreshMetrics(), refreshSamples(), refreshCases(), refreshBillCount()]);
}

function wireLoginOnce() {
  if (wireLoginOnce._done) return;
  wireLoginOnce._done = true;
  $("#btnLogin").addEventListener("click", doLogin);
  $("#loginPassword").addEventListener("keydown", (e) => {
    if (e.key === "Enter") doLogin();
  });
}

async function doLogin() {
  const password = $("#loginPassword").value;
  $("#loginHint").textContent = "Signing in…";
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    const r = await res.json().catch(() => ({}));
    if (!res.ok || r.ok === false) {
      $("#loginHint").textContent = r.detail || "Invalid password";
      return;
    }
    if (!r.auth_required) {
      $("#loginHint").textContent =
        "Server has no password set (CLEARANCE_PASSWORD empty). Open access mode.";
    }
    showLogin(false);
    await boot();
  } catch (e) {
    $("#loginHint").textContent = e.message;
  }
}

async function doLogout() {
  await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
  toast("Signed out");
  if (authRequired) {
    showLogin(true);
    $("#btnLogout").classList.add("hidden");
    $("#loginPassword").value = "";
    $("#loginHint").textContent = "Signed out. Enter password to continue.";
  }
}

async function runBench() {
  const btn = $("#btnBench");
  btn.disabled = true;
  try {
    const r = await api("/api/evals/benchmark?source=synthetic&limit=50");
    toast(`Bench ${r.cases} docs · micro ${pct(r.micro_field_accuracy)}`);
  } catch (e) {
    toast(`Bench failed: ${e.message}`);
  } finally {
    btn.disabled = false;
  }
}

async function runEval() {
  try {
    const e = await api("/api/evals/run");
    toast(`Gold eval · field ${pct(e.field_accuracy)}`);
  } catch (e) {
    toast(e.message);
  }
}

async function seedDemo() {
  const btn = $("#btnSeed");
  btn.disabled = true;
  try {
    const r = await api("/api/demo/seed", { method: "POST" });
    toast(`Seeded ${r.seeded} cases`);
    filterStatus = "";
    document.querySelectorAll("#statusTabs .tab").forEach((t) => {
      t.classList.toggle("active", (t.dataset.status || "") === "");
    });
    await Promise.all([refreshMetrics(), refreshCases(), refreshBillCount()]);
    if (r.cases?.length) await selectCase(r.cases[r.cases.length - 1].id);
  } catch (e) {
    toast(`Seed failed: ${e.message}`);
  } finally {
    btn.disabled = false;
  }
}

async function refreshMetrics() {
  const m = await api("/api/cases/metrics/summary");
  $("#mTotal").textContent = m.total_cases;
  $("#mAuto").textContent = m.auto_resolved;
  $("#mReview").textContent = m.needs_review;
  $("#mRate").textContent = pct(m.auto_resolve_rate);
  $("#mConf").textContent = pct(m.avg_confidence);
}

async function refreshBillCount() {
  try {
    const bills = await api("/api/bills");
    $("#mEval").textContent = bills.length;
  } catch {
    $("#mEval").textContent = "—";
  }
}

async function refreshSamples() {
  const box = $("#samples");
  box.innerHTML = "";
  if (!demoMode) return;
  const samples = await api("/api/samples");
  for (const name of samples.slice(0, 12)) {
    const btn = document.createElement("button");
    btn.className = "item";
    btn.innerHTML = `<div class="title">${escapeHtml(name)}</div><div class="meta">run sample</div>`;
    btn.onclick = () => runSample(name);
    box.appendChild(btn);
  }
}

async function refreshCases() {
  const params = new URLSearchParams();
  if (filterStatus) params.set("status", filterStatus);
  if (filterQ) params.set("q", filterQ);
  const qs = params.toString() ? `?${params}` : "";
  const cases = await api(`/api/cases${qs}`);
  const box = $("#caseList");
  box.innerHTML = "";
  if (!cases.length) {
    box.innerHTML = `<div class="hint">No cases in this queue.</div>`;
    return;
  }
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
  const created = await api(
    `/api/cases/from-sample/${name.split("/").map(encodeURIComponent).join("/")}`,
    { method: "POST" }
  );
  selectedId = created.id;
  toast(`${name} → ${created.status}`);
  filterStatus = created.status === "needs_review" ? "needs_review" : "";
  await Promise.all([refreshCases(), refreshMetrics(), selectCase(created.id)]);
}

async function onUpload(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    const res = await fetch("/api/cases", { method: "POST", body: fd, credentials: "include" });
    if (res.status === 401) {
      showLogin(true);
      return;
    }
    if (!res.ok) {
      toast(await res.text());
      return;
    }
    const created = await res.json();
    selectedId = created.id;
    e.target.value = "";
    toast(`Uploaded → ${created.status}`);
    filterStatus = created.status === "needs_review" ? "needs_review" : created.status;
    document.querySelectorAll("#statusTabs .tab").forEach((t) => {
      t.classList.toggle("active", (t.dataset.status || "") === filterStatus);
    });
    await Promise.all([refreshCases(), refreshMetrics(), refreshBillCount(), selectCase(created.id)]);
  } catch (err) {
    toast(err.message);
  }
}

async function selectCase(id) {
  selectedId = id;
  showView("inbox");
  await refreshCases();
  const c = await api(`/api/cases/${id}`);
  const root = $("#detail");
  const ext = c.extraction || {};
  const steps = c.steps || [];
  const validation = c.validation || {};
  const needsReview = c.status === "needs_review";
  const lines = ext.line_items || [];

  root.innerHTML = `
    <div class="detail-head">
      <div>
        <h2>${escapeHtml(ext.vendor_name || c.filename)}</h2>
        <div class="meta">
          <span class="status ${c.status}">${c.status}</span>
          ${c.decision ? `<span class="badge muted">${c.decision}</span>` : ""}
          ${c.erp_bill_id ? `<span class="badge">Bill ${escapeHtml(c.erp_bill_id)}</span>` : ""}
        </div>
      </div>
      <div class="detail-actions">
        <button class="btn ghost" id="btnExport">Export audit</button>
        <button class="btn ghost" id="btnArchive">Archive</button>
        <span class="badge muted">${escapeHtml(c.filename)}</span>
      </div>
    </div>

    ${
      needsReview
        ? `
    <div class="review-box">
      <h3>Review & correct fields</h3>
      <p class="detail">${escapeHtml(c.progress_ledger?.human_reason || "Confirm fields before posting.")}</p>
      <div class="form-grid">
        <label>Vendor <input id="fVendor" value="${escapeAttr(ext.vendor_name || "")}" /></label>
        <label>Invoice # <input id="fInv" value="${escapeAttr(ext.invoice_number || "")}" /></label>
        <label>Date <input id="fDate" value="${escapeAttr(ext.invoice_date || "")}" /></label>
        <label>Currency <input id="fCur" value="${escapeAttr(ext.currency || "USD")}" /></label>
        <label>Subtotal <input id="fSub" type="number" step="0.01" value="${ext.subtotal ?? 0}" /></label>
        <label>Tax <input id="fTax" type="number" step="0.01" value="${ext.tax ?? 0}" /></label>
        <label>Total <input id="fTotal" type="number" step="0.01" value="${ext.total ?? 0}" /></label>
        <label>Note <input id="reviewNote" placeholder="Optional audit note" /></label>
      </div>
      <div class="review-actions">
        <button class="btn" id="btnApproveEdit">Save & post bill</button>
        <button class="btn secondary" id="btnApprove">Approve as-is</button>
        <button class="btn secondary" id="btnReject">Reject</button>
      </div>
    </div>`
        : `
    <div class="kv">
      <div class="card"><div class="l">Invoice #</div><div class="v">${escapeHtml(ext.invoice_number || "—")}</div></div>
      <div class="card"><div class="l">Total</div><div class="v">${ext.total != null ? money(ext.total, ext.currency) : "—"}</div></div>
      <div class="card"><div class="l">Confidence</div><div class="v">${c.overall_confidence != null ? pct(c.overall_confidence) : "—"}</div></div>
      <div class="card"><div class="l">Date</div><div class="v">${escapeHtml(ext.invoice_date || "—")}</div></div>
    </div>`
    }

    ${
      lines.length
        ? `<h3 class="sub">Line items</h3>
      <table class="lines"><thead><tr><th>Description</th><th>Qty</th><th>Amount</th></tr></thead>
      <tbody>${lines
        .map(
          (li) =>
            `<tr><td>${escapeHtml(li.description || "")}</td><td>${li.quantity ?? ""}</td><td>${money(li.amount || 0, ext.currency)}</td></tr>`
        )
        .join("")}</tbody></table>`
        : ""
    }

    <h3 class="sub">Agent timeline</h3>
    <div class="timeline">
      ${steps
        .map(
          (s) => `
        <div class="step ${s.status}">
          <div class="name">${escapeHtml(s.name)}</div>
          <div>
            <div><span class="status ${s.status}">${s.status}</span></div>
            <div class="detail">${escapeHtml(s.detail || "")}</div>
          </div>
        </div>`
        )
        .join("")}
    </div>

    <h3 class="sub">Validation</h3>
    <div class="kv">
      <div class="card"><div class="l">OK</div><div class="v">${validation.ok ? "yes" : "no"}</div></div>
      <div class="card"><div class="l">Math</div><div class="v">${validation.math_ok ? "ok" : "fail"}</div></div>
      <div class="card"><div class="l">Policy</div><div class="v">${validation.policy_ok ? "ok" : "flagged"}</div></div>
    </div>
    ${(validation.issues || []).length ? `<pre class="audit">${escapeHtml((validation.issues || []).join("\n"))}</pre>` : ""}

    <h3 class="sub">Document preview</h3>
    <pre class="audit">${escapeHtml(c.content_preview || "")}</pre>

    <h3 class="sub">Audit log</h3>
    <pre class="audit">${escapeHtml(JSON.stringify(c.audit || [], null, 2))}</pre>
  `;

  $("#btnExport").onclick = () => exportAudit(id);
  $("#btnArchive").onclick = () => archiveCase(id);
  if (needsReview) {
    $("#btnApprove").onclick = () => review(id, "approve");
    $("#btnApproveEdit").onclick = () => review(id, "edit_and_approve", true);
    $("#btnReject").onclick = () => review(id, "reject");
  }
}

async function archiveCase(id) {
  await api(`/api/cases/${id}/archive`, { method: "POST" });
  toast("Case archived");
  selectedId = null;
  $("#detail").innerHTML = `<div class="empty"><h2>Case archived</h2><p>Select another case or upload a new invoice.</p></div>`;
  await Promise.all([refreshCases(), refreshMetrics()]);
}

async function exportAudit(id) {
  const bundle = await api(`/api/cases/${id}/export`);
  const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `clearance-audit-${id.slice(0, 8)}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
  toast("Audit downloaded");
}

async function review(id, action, withEdit = false) {
  const note = $("#reviewNote")?.value || "";
  let body = { action, note };
  if (withEdit || action === "edit_and_approve") {
    body.action = "edit_and_approve";
    body.extraction = {
      vendor_name: $("#fVendor").value,
      invoice_number: $("#fInv").value,
      invoice_date: $("#fDate").value,
      currency: $("#fCur").value || "USD",
      subtotal: parseFloat($("#fSub").value) || 0,
      tax: parseFloat($("#fTax").value) || 0,
      total: parseFloat($("#fTotal").value) || 0,
      vendor_confidence: 1,
      invoice_number_confidence: 1,
      invoice_date_confidence: 1,
      total_confidence: 1,
      line_items: [],
      raw_notes: "human-edited",
    };
  }
  await api(`/api/cases/${id}/review`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  toast(action === "reject" ? "Rejected" : "Posted — bill created");
  await Promise.all([refreshCases(), refreshMetrics(), refreshBillCount(), selectCase(id)]);
}

async function loadBills() {
  const bills = await api("/api/bills");
  const box = $("#billsTable");
  if (!bills.length) {
    box.innerHTML = `<p class="hint">No bills yet. Approve a case to post.</p>`;
    return;
  }
  box.innerHTML = `
    <table class="lines">
      <thead><tr>
        <th>Bill</th><th>Vendor</th><th>Invoice #</th><th>Date</th><th>Total</th><th>Status</th>
      </tr></thead>
      <tbody>
        ${bills
          .map(
            (b) => `<tr>
          <td>${escapeHtml(b.id)}</td>
          <td>${escapeHtml(b.vendor_name)}</td>
          <td>${escapeHtml(b.invoice_number)}</td>
          <td>${escapeHtml(b.invoice_date || "—")}</td>
          <td>${money(b.total, b.currency)}</td>
          <td>${escapeHtml(b.status)}</td>
        </tr>`
          )
          .join("")}
      </tbody>
    </table>`;
}

async function exportBillsCsv() {
  const res = await fetch("/api/bills/export.csv", { credentials: "include" });
  if (!res.ok) {
    toast("Export failed");
    return;
  }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "clearance-bills.csv";
  a.click();
  URL.revokeObjectURL(a.href);
  toast("Bills CSV downloaded");
}

async function loadSettings() {
  const s = await api("/api/settings");
  $("#setCompany").value = s.company_name || "";
  $("#setVendors").value = (s.known_vendors || []).join("\n");
  $("#setHigh").value = s.high_value_threshold;
  $("#setUnk").value = s.unknown_vendor_threshold;
  $("#setConf").value = s.confidence_hitl_threshold;
  $("#setCurr").value = (s.allowed_currencies || []).join(", ");
  $("#companyTag").textContent = s.company_name || "AP document operations";
}

async function saveSettings() {
  const body = {
    company_name: $("#setCompany").value,
    known_vendors: $("#setVendors").value
      .split("\n")
      .map((x) => x.trim())
      .filter(Boolean),
    high_value_threshold: parseFloat($("#setHigh").value),
    unknown_vendor_threshold: parseFloat($("#setUnk").value),
    confidence_hitl_threshold: parseFloat($("#setConf").value),
    allowed_currencies: $("#setCurr").value
      .split(",")
      .map((x) => x.trim().toUpperCase())
      .filter(Boolean),
  };
  await api("/api/settings", { method: "PUT", body: JSON.stringify(body) });
  toast("Settings saved");
  $("#companyTag").textContent = body.company_name;
}

function pct(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${Math.round(n * 1000) / 10}%`;
}
function money(n, currency = "USD") {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "USD",
    }).format(n);
  } catch {
    return `${n} ${currency || ""}`;
  }
}
function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
function escapeAttr(s) {
  return escapeHtml(s).replaceAll("'", "&#39;");
}

boot().catch((e) => {
  console.error(e);
  if (!authRequired) {
    $("#detail").innerHTML = `<div class="empty"><h2>API error</h2><p>${escapeHtml(e.message)}</p></div>`;
  }
});
