/* ============================================================
   AEGIS · Ezor Media — frontend logic
   ============================================================ */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const state = {
  agents: [],
  outputs: {},
  brief: {},
  runId: null,
  mode: "DEMO",
};

/* ---------- Boot ---------- */
init();

async function init() {
  try {
    const res = await fetch("/api/health");
    const h = await res.json();
    state.mode = h.mode;
    const pill = $("#modePill");
    pill.textContent = h.mode;
    pill.className = "pill " + (h.mode === "LIVE" ? "pill--live" : "pill--demo");
    $("#footMode").textContent =
      h.mode === "LIVE" ? `LIVE · ${h.model}` : "DEMO · set ANTHROPIC_API_KEY for live AI";
  } catch (e) {
    $("#footMode").textContent = "offline";
  }

  $("#runBtn").addEventListener("click", startRun);
  $("#sampleBtn").addEventListener("click", loadSample);
  $("#newRunBtn").addEventListener("click", resetToCompose);
  $("#historyBtn").addEventListener("click", openHistory);
  $("#closeHistory").addEventListener("click", closeHistory);
  $("#drawerScrim").addEventListener("click", closeHistory);
  $("#downloadBtn").addEventListener("click", downloadBrief);
  $("#copyBtn").addEventListener("click", copyBrief);
}

function loadSample() {
  $("#f_brand").value = "Aurelia Skincare";
  $("#f_product").value = "Launch of a premium vitamin-C glow serum";
  $("#f_goal").value = "Drive 2,000 launch-week orders and build a founding community";
  $("#f_audience").value = "Women 25–35, metro & tier-1 India, skincare-curious";
  $("#f_market").value = "India — metro + tier-1 cities";
  $("#f_budget").value = "₹15,00,000";
  $("#f_timeline").value = "6-week flight, festive-adjacent";
  $("#f_notes").value = "Clean, dermat-backed positioning; founder is on camera-comfortable";
}

function collectBrief() {
  return {
    brand: $("#f_brand").value.trim(),
    product: $("#f_product").value.trim(),
    goal: $("#f_goal").value.trim(),
    audience: $("#f_audience").value.trim(),
    market: $("#f_market").value.trim(),
    budget: $("#f_budget").value.trim(),
    timeline: $("#f_timeline").value.trim(),
    notes: $("#f_notes").value.trim(),
  };
}

/* ---------- Run ---------- */
async function startRun() {
  const brief = collectBrief();
  if (!brief.brand && !brief.product) {
    flashField();
    return;
  }
  state.brief = brief;
  state.outputs = {};

  // switch stage
  document.body.dataset.stage = "run";
  $("#compose").hidden = true;
  $("#run").hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });

  // reset document
  $("#docBrand").textContent = brief.brand || brief.product || "Campaign";
  $("#docMeta").textContent = "";
  $("#docBody").innerHTML = "";
  $("#docActions").hidden = true;
  $("#relayList").innerHTML = "";
  setCharge(0);
  setStatus("Connecting pipeline…");

  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(brief),
    });
    await consumeSSE(res.body.getReader());
  } catch (e) {
    setStatus("Connection error — " + e.message);
  }
}

/* Parse a fetch SSE stream (POST, so EventSource can't be used). */
async function consumeSSE(reader) {
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop(); // keep incomplete frame
    for (const frame of frames) {
      if (!frame.trim()) continue;
      let event = "message";
      let dataLine = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLine += line.slice(5).trim();
      }
      if (dataLine) handleEvent(event, JSON.parse(dataLine));
    }
  }
}

/* ---------- Event handling ---------- */
function handleEvent(event, data) {
  switch (event) {
    case "run_started":
      state.runId = data.run_id;
      state.mode = data.mode;
      state.agents = data.agents;
      buildRelay(data.agents);
      buildSections(data.agents);
      $("#docMeta").textContent =
        `${data.agents.length} agents · ${data.mode} mode · ${new Date().toLocaleString()}`;
      setStatus("Pipeline live");
      break;

    case "agent_started":
      markNode(data.id, "active");
      setStatus(`Running · ${data.name}`);
      $(`#sec-body-${data.id}`).classList.add("streaming");
      scrollSectionIntoView(data.id);
      break;

    case "agent_chunk":
      state.outputs[data.id] = (state.outputs[data.id] || "") + data.text;
      renderSection(data.id, state.outputs[data.id], true);
      break;

    case "agent_done": {
      markNode(data.id, "done");
      $(`#sec-body-${data.id}`).classList.remove("streaming");
      renderSection(data.id, state.outputs[data.id], false);
      advanceCharge();
      break;
    }

    case "agent_error":
      markNode(data.id, "error");
      $(`#sec-body-${data.id}`).classList.remove("streaming");
      renderSection(data.id, `_Agent error: ${data.error}_`, false);
      advanceCharge();
      break;

    case "run_complete":
      setStatus("Brief complete", true);
      setCharge(100);
      $("#docActions").hidden = false;
      break;
  }
}

/* ---------- Relay ---------- */
function buildRelay(agents) {
  const list = $("#relayList");
  list.innerHTML = "";
  agents.forEach((a) => {
    const li = document.createElement("li");
    li.className = "relaynode";
    li.id = `node-${a.id}`;
    li.innerHTML = `
      <div class="relaynode__dot">${a.icon}</div>
      <div class="relaynode__body">
        <div class="relaynode__name">${a.name}</div>
        <div class="relaynode__role">${a.role}</div>
      </div>`;
    list.appendChild(li);
  });
}

function markNode(id, status) {
  const node = $(`#node-${id}`);
  if (!node) return;
  node.classList.remove("is-active", "is-done", "is-error");
  if (status === "active") node.classList.add("is-active");
  if (status === "done") {
    node.classList.add("is-done");
    node.querySelector(".relaynode__dot").innerHTML = "&#10003;";
  }
  if (status === "error") node.classList.add("is-error");
}

let chargeStep = 0;
function advanceCharge() {
  chargeStep++;
  const pct = Math.round((chargeStep / state.agents.length) * 100);
  setCharge(pct);
}
function setCharge(pct) {
  if (pct === 0) chargeStep = 0;
  $("#relayList").style.setProperty("--charge", pct + "%");
}

function setStatus(text, complete = false) {
  const el = $("#runStatus");
  el.textContent = text;
  el.classList.toggle("is-complete", complete);
}

/* ---------- Document sections ---------- */
function buildSections(agents) {
  const body = $("#docBody");
  body.innerHTML = "";
  agents.forEach((a, i) => {
    const sec = document.createElement("section");
    sec.className = "docsection";
    sec.style.animationDelay = `${i * 0.05}s`;
    sec.innerHTML = `
      <div class="docsection__head">
        <span class="docsection__num">${a.icon}</span>
        <h3 class="docsection__title">${a.name}</h3>
        <span class="docsection__role">${a.role}</span>
      </div>
      <div class="md" id="sec-body-${a.id}"></div>`;
    body.appendChild(sec);
  });
}

function renderSection(id, raw, streaming) {
  const el = $(`#sec-body-${id}`);
  if (!el) return;
  el.innerHTML = mdToHtml(raw || "");
}

function scrollSectionIntoView(id) {
  const node = $(`#node-${id}`);
  if (node) node.scrollIntoView({ behavior: "smooth", block: "center" });
}

/* ---------- Reset / history ---------- */
function resetToCompose() {
  document.body.dataset.stage = "compose";
  $("#run").hidden = true;
  $("#compose").hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function openHistory() {
  $("#historyDrawer").hidden = false;
  const list = $("#historyList");
  list.innerHTML = `<li class="history__empty">Loading…</li>`;
  try {
    const res = await fetch("/api/runs");
    const runs = await res.json();
    if (!runs.length) {
      list.innerHTML = `<li class="history__empty">No runs yet. Generate your first campaign.</li>`;
      return;
    }
    list.innerHTML = "";
    runs.forEach((r) => {
      const li = document.createElement("li");
      li.className = "historyitem";
      const when = new Date(r.created_at * 1000).toLocaleString();
      li.innerHTML = `
        <div class="historyitem__brand">${r.brief.brand || r.brief.product || "Untitled brief"}</div>
        <div class="historyitem__meta">${r.mode} · ${r.status} · ${when}</div>`;
      li.addEventListener("click", () => loadRun(r.id));
      list.appendChild(li);
    });
  } catch (e) {
    list.innerHTML = `<li class="history__empty">Could not load history.</li>`;
  }
}

function closeHistory() {
  $("#historyDrawer").hidden = true;
}

async function loadRun(runId) {
  closeHistory();
  const res = await fetch(`/api/runs/${runId}`);
  const run = await res.json();
  state.runId = runId;
  state.brief = run.brief;
  state.outputs = run.outputs;
  state.agents = state.agents.length ? state.agents : defaultAgents();

  document.body.dataset.stage = "run";
  $("#compose").hidden = true;
  $("#run").hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });

  $("#docBrand").textContent = run.brief.brand || run.brief.product || "Campaign";
  $("#docMeta").textContent =
    `${run.mode} mode · ${new Date(run.created_at * 1000).toLocaleString()}`;

  buildRelay(state.agents);
  buildSections(state.agents);
  state.agents.forEach((a) => {
    markNode(a.id, "done");
    renderSection(a.id, run.outputs[a.id] || "_No output._", false);
  });
  setCharge(100);
  setStatus("Loaded from history", true);
  $("#docActions").hidden = false;
}

function defaultAgents() {
  return [
    { id: "research", name: "Research", role: "Audience, market & cultural signals", icon: "01" },
    { id: "competitor", name: "Competitor", role: "Positioning gaps & rival activity", icon: "02" },
    { id: "strategy", name: "Strategy", role: "Campaign concept, pillars & KPIs", icon: "03" },
    { id: "creative", name: "Creative", role: "Hooks, copy & content calendar", icon: "04" },
    { id: "media", name: "Media & Budget", role: "Channel mix & spend allocation", icon: "05" },
  ];
}

/* ---------- Export ---------- */
function downloadBrief() {
  if (!state.runId) return;
  window.location.href = `/api/runs/${state.runId}/export.md`;
}

async function copyBrief() {
  if (!state.runId) return;
  const res = await fetch(`/api/runs/${state.runId}/export.md`);
  const text = await res.text();
  try {
    await navigator.clipboard.writeText(text);
    const btn = $("#copyBtn");
    const old = btn.textContent;
    btn.textContent = "Copied ✓";
    setTimeout(() => (btn.textContent = old), 1600);
  } catch (e) {
    alert("Copy failed — your browser blocked clipboard access.");
  }
}

function flashField() {
  const el = $("#f_brand");
  el.style.borderColor = "var(--clay)";
  el.focus();
  setTimeout(() => (el.style.borderColor = ""), 1200);
}

/* ============================================================
   Minimal, self-contained Markdown → HTML
   Handles: headings, bold, italic, blockquote, lists, tables,
   horizontal rules, paragraphs. No external dependency.
   ============================================================ */
function mdToHtml(md) {
  const esc = (s) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const inline = (s) =>
    esc(s)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*\n]+?)\*/g, "$1<em>$2</em>")
      .replace(/`([^`]+?)`/g, "<code>$1</code>");

  const lines = md.replace(/\r/g, "").split("\n");
  let html = "";
  let i = 0;

  while (i < lines.length) {
    let line = lines[i];

    // blank
    if (!line.trim()) { i++; continue; }

    // horizontal rule
    if (/^---+$/.test(line.trim())) { html += "<hr/>"; i++; continue; }

    // headings
    const h = line.match(/^(#{1,3})\s+(.*)/);
    if (h) {
      const lvl = h[1].length;
      html += `<h${lvl}>${inline(h[2])}</h${lvl}>`;
      i++;
      continue;
    }

    // blockquote
    if (line.startsWith(">")) {
      const buf = [];
      while (i < lines.length && lines[i].startsWith(">")) {
        buf.push(lines[i].replace(/^>\s?/, ""));
        i++;
      }
      html += `<blockquote>${inline(buf.join(" "))}</blockquote>`;
      continue;
    }

    // table (needs a header row + separator row)
    if (line.includes("|") && i + 1 < lines.length && /^\s*\|?[\s:|-]+\|?\s*$/.test(lines[i + 1]) && lines[i + 1].includes("-")) {
      const header = splitRow(line);
      i += 2; // skip header + separator
      let body = "";
      while (i < lines.length && lines[i].includes("|") && lines[i].trim()) {
        const cells = splitRow(lines[i]);
        body += "<tr>" + cells.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>";
        i++;
      }
      html +=
        "<table><thead><tr>" +
        header.map((c) => `<th>${inline(c)}</th>`).join("") +
        "</tr></thead><tbody>" + body + "</tbody></table>";
      continue;
    }

    // unordered list
    if (/^\s*[-*]\s+/.test(line)) {
      let items = "";
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items += `<li>${inline(lines[i].replace(/^\s*[-*]\s+/, ""))}</li>`;
        i++;
      }
      html += `<ul>${items}</ul>`;
      continue;
    }

    // paragraph (gather consecutive non-empty, non-special lines)
    const para = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^(#{1,3}\s|>|\s*[-*]\s|---+$)/.test(lines[i]) &&
      !lines[i].includes("|")
    ) {
      para.push(lines[i]);
      i++;
    }
    if (para.length) html += `<p>${inline(para.join(" "))}</p>`;
    else i++; // safety
  }

  return html;
}

function splitRow(row) {
  return row
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((c) => c.trim());
}
