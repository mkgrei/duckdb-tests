/* Playground: guided tour, free-form SQL, live DB state panel. */

const $ = (sel) => document.querySelector(sel);

let prevState = null; // previous /api/state snapshot, for change-flashing
const doneSteps = new Set();

/* ---------- API helpers ---------- */

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...opts,
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
  return body;
}

/* ---------- DB state panel ---------- */

function renderState(state) {
  const wrap = $("#state-tables");
  const prevByName = new Map(
    (prevState?.tables || []).map((t) => [t.name, t])
  );
  wrap.innerHTML = "";

  if (!state.tables.length) {
    wrap.innerHTML = `<div class="state-empty">No tables yet — run tour step 1 to ingest the CSV.</div>`;
  }

  for (const t of state.tables) {
    const prev = prevByName.get(t.name);
    const isNew = prevState !== null && !prev;
    const changed = prev && prev.row_count !== t.row_count;

    const div = document.createElement("div");
    div.className = "state-table" + (isNew || changed ? " flash" : "");
    div.innerHTML = `
      <header>
        <span>${t.name} ${isNew ? "✨" : ""}</span>
        <span class="rc ${changed ? "flash" : ""}">${t.row_count.toLocaleString()} rows</span>
      </header>
      <div class="cols">${t.columns.map((c) => `${c.name} <span style="opacity:.6">${c.type}</span>`).join("<br>")}</div>
    `;
    div.querySelector("header").addEventListener("click", () => div.classList.toggle("open"));
    wrap.appendChild(div);
  }

  const kb = (state.db_file_bytes / 1024).toFixed(0);
  $("#state-meta").innerHTML = `
    <div>file: data/playground.duckdb</div>
    <div>size: ${kb} KB</div>
    <div>duckdb v${state.duckdb_version}</div>
  `;
  prevState = state;
}

async function refreshState() {
  renderState(await api("/api/state"));
}

/* ---------- results rendering ---------- */

function renderResult(result) {
  const wrap = $("#results-wrap");
  const meta = $("#results-meta");
  if (!result.columns.length) {
    wrap.innerHTML = "";
    meta.textContent = `OK — statement executed in ${result.elapsed_ms} ms (no result set)`;
    return;
  }
  const head = result.columns.map((c) => `<th>${c}</th>`).join("");
  const body = result.rows
    .map(
      (row) =>
        `<tr>${row
          .map((v) => (v === null ? `<td class="null">∅</td>` : `<td>${v}</td>`))
          .join("")}</tr>`
    )
    .join("");
  wrap.innerHTML = `<table class="results"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
  meta.textContent =
    `${result.row_count} row${result.row_count === 1 ? "" : "s"}` +
    (result.truncated ? " (truncated to 500)" : "") +
    ` · ${result.elapsed_ms} ms`;
}

function showError(message) {
  const box = $("#error-box");
  box.textContent = message;
  box.classList.add("show");
}

function clearFeedback() {
  $("#error-box").classList.remove("show");
  $("#explanation").classList.remove("show");
  $("#explain-pane").classList.remove("show");
  $("#results-wrap").innerHTML = "";
  $("#results-meta").textContent = "";
}

/* ---------- free-form run / explain ---------- */

async function runSql() {
  clearFeedback();
  const sql = $("#sql-editor").value.trim();
  if (!sql) return;
  try {
    const result = await api("/api/query", { method: "POST", body: JSON.stringify({ sql }) });
    renderResult(result);
  } catch (e) {
    showError(e.message);
  }
  await refreshState();
}

async function explainSql(analyze) {
  $("#error-box").classList.remove("show");
  const sql = $("#sql-editor").value.trim();
  if (!sql) return;
  try {
    const { plan } = await api("/api/explain", {
      method: "POST",
      body: JSON.stringify({ sql, analyze }),
    });
    $("#explain-text").textContent = plan;
    $("#explain-pane").classList.add("show");
    if (analyze) await refreshState(); // EXPLAIN ANALYZE actually executes
  } catch (e) {
    showError(e.message);
  }
}

/* ---------- guided tour ---------- */

async function loadTour() {
  const { actions } = await api("/api/actions");
  const tour = $("#tour");
  tour.innerHTML = "";
  for (const action of actions) {
    const step = document.createElement("div");
    step.className = "tour-step";
    step.innerHTML = `
      <header>
        <span>${action.title}</span>
        <span class="status" data-status></span>
      </header>
      <div class="body">
        <span class="cat">${action.category}</span>
        <p style="margin:4px 0 10px">${action.description}</p>
        <button class="primary" style="font-size:.85rem;padding:6px 14px">▶ Run this step</button>
      </div>
    `;
    step.querySelector("header").addEventListener("click", () => step.classList.toggle("open"));
    step.querySelector("button").addEventListener("click", (ev) => {
      ev.stopPropagation();
      runAction(action, step);
    });
    tour.appendChild(step);
  }
}

async function runAction(action, stepEl) {
  clearFeedback();
  $("#sql-editor").value = action.sql; // copy SQL in so users can tweak & re-run
  try {
    const { result, state } = await api(`/api/actions/${action.id}`, { method: "POST" });
    renderResult(result);
    renderState(state);
    $("#explanation-text").textContent = action.teaches;
    $("#explanation").classList.add("show");
    doneSteps.add(action.id);
    stepEl.querySelector("[data-status]").textContent = "✓ done";
  } catch (e) {
    showError(e.message);
    await refreshState();
  }
}

/* ---------- reset ---------- */

async function resetDb() {
  clearFeedback();
  const { state } = await api("/api/reset", { method: "POST" });
  prevState = null; // don't flash everything as "new"
  renderState(state);
  doneSteps.clear();
  document.querySelectorAll("[data-status]").forEach((el) => (el.textContent = ""));
  $("#results-meta").textContent = "Database reset: file deleted, reconnected, sales reseeded from CSV.";
}

/* ---------- wire up ---------- */

$("#btn-run").addEventListener("click", runSql);
$("#btn-explain").addEventListener("click", () => explainSql(false));
$("#btn-explain-analyze").addEventListener("click", () => explainSql(true));
$("#btn-reset").addEventListener("click", resetDb);
$("#sql-editor").addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") runSql();
});

refreshState();
loadTour();
