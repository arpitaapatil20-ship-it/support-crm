/* ═══════════════════════════════════════════════════════
   SupportDesk CRM  —  static/app.js
   ═══════════════════════════════════════════════════════ */

"use strict";

// ── State ─────────────────────────────────────────────
const state = {
    view: "dashboard",   // dashboard | tickets | detail
    filter: { status: "All", priority: "All", search: "", sort: "created_at", order: "desc" },
    searchTimer: null,
};

// ── API helpers ───────────────────────────────────────
async function api(path, opts = {}) {
    const res = await fetch("/api" + path, {
        headers: { "Content-Type": "application/json" },
        ...opts,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
}

// ── Navigation ────────────────────────────────────────
function navigate(view, extra = {}) {
    state.view = view;

    // Update active sidebar item
    document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
    const navEl = document.getElementById("nav-" + view);
    if (navEl) navEl.classList.add("active");

    // Close mobile sidebar
    document.getElementById("sidebar").classList.remove("open");

    if (view === "dashboard") {
        document.getElementById("topbar-title").textContent = "Dashboard";
        renderDashboard();
    } else if (view === "tickets") {
        if (extra.status) state.filter.status = extra.status;
        document.getElementById("topbar-title").textContent = "All Tickets";
        renderTicketList();
    } else if (view === "detail") {
        document.getElementById("topbar-title").innerHTML =
            `<span class="crumb">Tickets /</span> ${extra.id}`;
        renderDetail(extra.id);
    }
}

function navWithFilter(status) {
    state.filter.status = status;
    navigate("tickets");
}

function toggleSidebar() {
    document.getElementById("sidebar").classList.toggle("open");
}

// ── Dashboard ─────────────────────────────────────────
async function renderDashboard() {
    setPage(`<div class="loading-state"><div class="spinner"></div> Loading…</div>`);
    try {
        const { stats, recent } = await api("/stats");
        updateBadge(stats.open);

        setPage(`
      <div class="page-header">
        <div>
          <h1>Welcome back 👋</h1>
          <div class="sub">Here's what's happening in your support queue.</div>
        </div>
        <button class="btn btn-primary" onclick="openCreateModal()">＋ New Ticket</button>
      </div>

      <div class="stat-grid">
        <div class="stat-card s-total">
          <div class="stat-label">Total</div>
          <div class="stat-value">${stats.total}</div>
        </div>
        <div class="stat-card s-open clickable" onclick="navWithFilter('Open')">
          <div class="stat-label">Open</div>
          <div class="stat-value">${stats.open}</div>
        </div>
        <div class="stat-card s-inprog clickable" onclick="navWithFilter('In Progress')">
          <div class="stat-label">In Progress</div>
          <div class="stat-value">${stats.in_progress}</div>
        </div>
        <div class="stat-card s-closed clickable" onclick="navWithFilter('Closed')">
          <div class="stat-label">Closed</div>
          <div class="stat-value">${stats.closed}</div>
        </div>
        <div class="stat-card s-urgent">
          <div class="stat-label">Urgent</div>
          <div class="stat-value">${stats.urgent || 0}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3>Recent Tickets</h3>
          <button class="btn btn-ghost btn-sm" onclick="navigate('tickets')">View all →</button>
        </div>
        <div class="table-wrap" style="border:none;border-radius:0">
          <table class="ticket-table">
            <thead>
              <tr>
                <th>ID</th><th>Customer</th><th>Subject</th>
                <th>Priority</th><th>Status</th><th>Date</th>
              </tr>
            </thead>
            <tbody>
              ${recent.length
                ? recent.map(t => rowBasic(t)).join("")
                : `<tr><td colspan="6">${emptyState("📭", "No tickets yet", "Create your first ticket to get started")}</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    `);
    } catch (err) { setPage(errorState(err.message)); }
}

// ── Ticket List ───────────────────────────────────────
async function renderTicketList() {
    setPage(`<div class="loading-state"><div class="spinner"></div> Loading tickets…</div>`);
    await fetchTickets();
}

async function fetchTickets() {
    const f = state.filter;
    const q = new URLSearchParams();
    if (f.status && f.status !== "All") q.set("status", f.status);
    if (f.priority && f.priority !== "All") q.set("priority", f.priority);
    if (f.search) q.set("search", f.search);
    q.set("sort", f.sort);
    q.set("order", f.order);

    try {
        const { tickets, stats } = await api("/tickets?" + q);
        updateBadge(stats?.open || 0);
        renderTicketsUI(tickets, stats);
    } catch (err) { setPage(errorState(err.message)); }
}

function renderTicketsUI(tickets, stats) {
    const f = state.filter;
    setPage(`
    <div class="page-header">
      <div>
        <h1>Support Tickets</h1>
        <div class="sub">${stats ? `${stats.total} total · ${stats.open} open` : ""}</div>
      </div>
      <button class="btn btn-primary" onclick="openCreateModal()">＋ New Ticket</button>
    </div>

    <div class="filter-bar">
      <div class="filter-group">
        ${["All", "Open", "In Progress", "Closed"].map(s =>
        `<button class="filter-btn ${statusFCls(s)} ${f.status === s ? "active" : ""}"
             onclick="setFilter('status','${s}')">${s}</button>`
    ).join("")}
      </div>
      <select class="select-filter" onchange="setFilter('priority',this.value)">
        ${["All", "Low", "Medium", "High", "Urgent"].map(p =>
        `<option value="${p}" ${f.priority === p ? "selected" : ""}>${p === "All" ? "All Priorities" : p}</option>`
    ).join("")}
      </select>
      <select class="select-filter" onchange="setSort(this.value)">
        <option value="created_at" ${f.sort === "created_at" ? "selected" : ""}>Newest first</option>
        <option value="updated_at" ${f.sort === "updated_at" ? "selected" : ""}>Recently updated</option>
        <option value="customer_name" ${f.sort === "customer_name" ? "selected" : ""}>Customer A–Z</option>
        <option value="priority"  ${f.sort === "priority" ? "selected" : ""}>Priority</option>
        <option value="status"    ${f.sort === "status" ? "selected" : ""}>Status</option>
      </select>
      <span class="results-count">${tickets.length} result${tickets.length !== 1 ? "s" : ""}</span>
    </div>

    <div class="table-wrap">
      <table class="ticket-table">
        <thead>
          <tr>
            <th>Ticket ID</th><th>Customer</th><th>Subject</th>
            <th>Priority</th><th>Status</th><th>Created</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${tickets.length
            ? tickets.map(t => rowFull(t)).join("")
            : `<tr><td colspan="7">${emptyState("🔍", "No tickets found", "Try adjusting your search or filters")}</td></tr>`}
        </tbody>
      </table>
    </div>
  `);
}

// ── Ticket Detail ─────────────────────────────────────
async function renderDetail(id) {
    setPage(`<div class="loading-state"><div class="spinner"></div> Loading ticket…</div>`);
    try {
        const t = await api("/tickets/" + id);
        renderDetailUI(t);
    } catch (err) { setPage(errorState(err.message)); }
}

function renderDetailUI(t) {
    setPage(`
    <button class="back-link" onclick="navigate('tickets')">← Back to Tickets</button>

    <div class="detail-grid">

      <!-- Left column -->
      <div>
        <div class="card" style="margin-bottom:20px">
          <div class="card-header">
            <h3>Ticket Details</h3>
            <span class="t-id">${t.ticket_id}</span>
          </div>
          <div class="card-body">
            <div class="detail-meta">${priBadge(t.priority)} ${statusBadge(t.status)}</div>
            <div class="detail-subject">${esc(t.subject)}</div>
            <div class="detail-desc">${esc(t.description)}</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3>💬 Notes &amp; Updates</h3>
            <span style="font-size:12px;color:var(--muted)">${t.notes.length} note${t.notes.length !== 1 ? "s" : ""}</span>
          </div>
          <div class="card-body">
            <div id="notes-list">
              ${t.notes.length
            ? t.notes.map(noteHTML).join("")
            : `<p style="color:var(--muted);font-size:13px">No notes yet — add the first one below.</p>`}
            </div>
            <div class="divider"></div>
            <div class="form-group" style="margin-bottom:10px">
              <label class="form-label">Add a Note</label>
              <textarea class="form-control" id="note-input" placeholder="Write an update or resolution…"></textarea>
            </div>
            <div style="display:flex;gap:10px;align-items:center;justify-content:flex-end">
              <input class="form-control" id="note-author" value="Support Agent"
                placeholder="Your name" style="max-width:160px;padding:7px 10px;font-size:12.5px" />
              <button class="btn btn-primary btn-sm" onclick="submitNote('${t.ticket_id}')">Post Note</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right column -->
      <div>
        <div class="card" style="margin-bottom:16px">
          <div class="card-header"><h3>⚙ Manage</h3></div>
          <div class="card-body">
            <div class="form-group" style="margin-bottom:14px">
              <label class="form-label">Status</label>
              <select class="form-control" onchange="patchTicket('${t.ticket_id}','status',this.value)">
                ${["Open", "In Progress", "Closed"].map(s =>
                `<option ${t.status === s ? "selected" : ""}>${s}</option>`
            ).join("")}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Priority</label>
              <select class="form-control" onchange="patchTicket('${t.ticket_id}','priority',this.value)">
                ${["Low", "Medium", "High", "Urgent"].map(p =>
                `<option ${t.priority === p ? "selected" : ""}>${p}</option>`
            ).join("")}
              </select>
            </div>
          </div>
        </div>

        <div class="card" style="margin-bottom:16px">
          <div class="card-header"><h3>👤 Customer</h3></div>
          <div class="card-body">
            <div class="info-row"><span class="lbl">Name</span>  <span class="val">${esc(t.customer_name)}</span></div>
            <div class="info-row"><span class="lbl">Email</span> <span class="val mono">${esc(t.customer_email)}</span></div>
            <div class="info-row"><span class="lbl">Ticket</span><span class="val mono">${t.ticket_id}</span></div>
            <div class="info-row"><span class="lbl">Created</span><span class="val">${fmtDate(t.created_at)}</span></div>
            <div class="info-row"><span class="lbl">Updated</span><span class="val">${fmtDate(t.updated_at)}</span></div>
          </div>
        </div>

        <button class="btn btn-danger" style="width:100%"
          onclick="deleteTicket('${t.ticket_id}',true)">🗑 Delete Ticket</button>
      </div>

    </div>
  `);
}

function noteHTML(n) {
    return `
    <div class="note">
      <div class="note-meta">
        <span class="note-author">👤 ${esc(n.author)}</span>
        <span class="note-time">${relDate(n.created_at)}</span>
      </div>
      <div class="note-text">${esc(n.note_text)}</div>
    </div>`;
}

// ── Actions ───────────────────────────────────────────
async function patchTicket(id, field, value) {
    try {
        await api("/tickets/" + id, { method: "PUT", body: JSON.stringify({ [field]: value }) });
        toast("success", "Updated", `${cap(field)} → "${value}"`);
    } catch (err) { toast("error", "Error", err.message); }
}

async function submitNote(id) {
    const text = (document.getElementById("note-input").value || "").trim();
    const author = (document.getElementById("note-author").value || "Support Agent").trim();
    if (!text) { toast("info", "Empty note", "Write something before posting"); return; }
    try {
        await api("/tickets/" + id, { method: "PUT", body: JSON.stringify({ note: text, author }) });
        document.getElementById("note-input").value = "";
        const t = await api("/tickets/" + id);
        document.getElementById("notes-list").innerHTML = t.notes.map(noteHTML).join("");
        toast("success", "Note added");
    } catch (err) { toast("error", "Error", err.message); }
}

async function deleteTicket(id, fromDetail = false) {
    if (!confirm(`Delete ticket ${id}? This cannot be undone.`)) return;
    try {
        await api("/tickets/" + id, { method: "DELETE" });
        toast("success", "Deleted", `${id} removed`);
        fromDetail ? navigate("tickets") : fetchTickets();
    } catch (err) { toast("error", "Error", err.message); }
}

// ── Create Modal ──────────────────────────────────────
function openCreateModal() {
    ["f-name", "f-email", "f-subject", "f-description"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = "";
    });
    ["e-name", "e-email", "e-subject", "e-description"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = "";
    });
    const pEl = document.getElementById("f-priority");
    if (pEl) pEl.value = "Medium";
    document.getElementById("create-modal").style.display = "flex";
    setTimeout(() => { const el = document.getElementById("f-name"); if (el) el.focus(); }, 60);
}

function closeModal(id) {
    document.getElementById(id).style.display = "none";
}

function overlayClick(e, id) {
    if (e.target.classList.contains("overlay")) closeModal(id);
}

function validate() {
    const rules = [
        { id: "f-name", err: "e-name", msg: "Name is required" },
        { id: "f-email", err: "e-email", msg: "Valid email is required", email: true },
        { id: "f-subject", err: "e-subject", msg: "Subject is required" },
        { id: "f-description", err: "e-description", msg: "Description is required" },
    ];
    let ok = true;
    rules.forEach(({ id, err, msg, email }) => {
        const el = document.getElementById(id);
        const eEl = document.getElementById(err);
        el.classList.remove("has-error");
        eEl.textContent = "";
        const v = el.value.trim();
        if (!v) { eEl.textContent = msg; el.classList.add("has-error"); ok = false; }
        else if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) {
            eEl.textContent = "Enter a valid email"; el.classList.add("has-error"); ok = false;
        }
    });
    return ok;
}

async function submitCreate() {
    if (!validate()) return;
    const btn = document.getElementById("create-btn");
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner" style="width:14px;height:14px;border-width:2px"></div> Creating…`;
    try {
        const data = await api("/tickets", {
            method: "POST",
            body: JSON.stringify({
                customer_name: document.getElementById("f-name").value.trim(),
                customer_email: document.getElementById("f-email").value.trim(),
                subject: document.getElementById("f-subject").value.trim(),
                description: document.getElementById("f-description").value.trim(),
                priority: document.getElementById("f-priority").value,
            }),
        });
        closeModal("create-modal");
        toast("success", "Ticket created!", data.ticket_id);
        navigate("detail", { id: data.ticket_id });
    } catch (err) {
        toast("error", "Failed", err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "Create Ticket";
    }
}

// ── Search & Filters ──────────────────────────────────
function handleSearch(val) {
    clearTimeout(state.searchTimer);
    state.filter.search = val;
    state.searchTimer = setTimeout(() => {
        if (state.view !== "tickets") navigate("tickets");
        else fetchTickets();
    }, 260);
}

function setFilter(key, val) {
    state.filter[key] = val;
    fetchTickets();
}

function setSort(val) {
    state.filter.sort = val;
    fetchTickets();
}

// ── Helpers ───────────────────────────────────────────
function setPage(html) {
    document.getElementById("page-content").innerHTML = html;
}

function updateBadge(n) {
    const el = document.getElementById("open-badge");
    if (el) el.textContent = n || 0;
}

function statusFCls(s) {
    return s === "Open" ? "f-open" : s === "In Progress" ? "f-inprog" : s === "Closed" ? "f-closed" : "";
}

function statusBCls(s) {
    return s === "Open" ? "b-open" : s === "In Progress" ? "b-prog" : "b-done";
}

function statusBadge(s) {
    return `<span class="badge ${statusBCls(s)}"><span class="badge-dot"></span>${s}</span>`;
}

function priBadge(p) {
    const cls = { Low: "pri-low", Medium: "pri-medium", High: "pri-high", Urgent: "pri-urgent" }[p] || "pri-medium";
    return `<span class="pri-badge ${cls}">${p}</span>`;
}

function relDate(iso) {
    if (!iso) return "—";
    const m = Math.floor((Date.now() - new Date(iso)) / 60000);
    if (m < 1) return "Just now";
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    const d = Math.floor(h / 24);
    if (d < 30) return `${d}d ago`;
    return fmtDate(iso);
}

function fmtDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-GB", {
        day: "2-digit", month: "short", year: "numeric",
    });
}

function esc(s) {
    return (s || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function cap(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function emptyState(icon, title, msg) {
    return `<div class="empty-state">
    <div class="es-icon">${icon}</div>
    <h3>${title}</h3>
    <p>${msg}</p>
  </div>`;
}

function errorState(msg) {
    return `<div class="empty-state">
    <div class="es-icon">⚠️</div>
    <h3>Something went wrong</h3>
    <p>${esc(msg)}</p>
  </div>`;
}

// Row templates
function rowBasic(t) {
    return `
    <tr onclick="navigate('detail',{id:'${t.ticket_id}'})">
      <td><span class="t-id">${t.ticket_id}</span></td>
      <td><div class="t-name">${esc(t.customer_name)}</div><div class="t-email">${esc(t.customer_email)}</div></td>
      <td class="t-subj">${esc(t.subject)}</td>
      <td>${priBadge(t.priority)}</td>
      <td>${statusBadge(t.status)}</td>
      <td class="t-date">${relDate(t.created_at)}</td>
    </tr>`;
}

function rowFull(t) {
    return `
    <tr onclick="navigate('detail',{id:'${t.ticket_id}'})">
      <td><span class="t-id">${t.ticket_id}</span></td>
      <td><div class="t-name">${esc(t.customer_name)}</div><div class="t-email">${esc(t.customer_email)}</div></td>
      <td class="t-subj">${esc(t.subject)}</td>
      <td>${priBadge(t.priority)}</td>
      <td>${statusBadge(t.status)}</td>
      <td class="t-date">${relDate(t.created_at)}</td>
      <td onclick="event.stopPropagation()">
        <div style="display:flex;gap:6px">
          <button class="btn btn-ghost btn-sm" onclick="navigate('detail',{id:'${t.ticket_id}'})">View</button>
          <button class="btn btn-danger btn-sm" onclick="deleteTicket('${t.ticket_id}')">✕</button>
        </div>
      </td>
    </tr>`;
}

// ── Toast ─────────────────────────────────────────────
function toast(type, title, msg = "") {
    const icons = { success: "✅", error: "❌", info: "ℹ️" };
    const el = document.createElement("div");
    el.className = `toast t-${type}`;
    el.innerHTML = `
    <span class="toast-icon">${icons[type] || "ℹ️"}</span>
    <div>
      <div class="toast-title">${esc(title)}</div>
      ${msg ? `<div class="toast-msg">${esc(msg)}</div>` : ""}
    </div>`;
    document.getElementById("toast-container").appendChild(el);
    setTimeout(() => {
        el.style.transition = "opacity .3s";
        el.style.opacity = "0";
        setTimeout(() => el.remove(), 300);
    }, 3400);
}

// ── Keyboard shortcuts ────────────────────────────────
document.addEventListener("keydown", e => {
    if (e.key === "Escape") {
        document.querySelectorAll(".overlay").forEach(el => el.style.display = "none");
        document.getElementById("sidebar").classList.remove("open");
    }
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        document.getElementById("global-search").focus();
    }
});

// ── Boot ──────────────────────────────────────────────
navigate("dashboard");
