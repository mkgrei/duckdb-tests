/* SVG diagram builders + animations for the Learn page.
   Everything is plain DOM/SVG — no libraries. */

const SVG_NS = "http://www.w3.org/2000/svg";

function svgEl(tag, attrs = {}, children = []) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  for (const c of children) el.appendChild(c);
  return el;
}

function svgText(str, attrs = {}) {
  const el = svgEl("text", attrs);
  el.textContent = str;
  return el;
}

/* =====================================================================
   1. Row-store vs column-store scan  (the centerpiece)
   Two 8x5 grids of the same table; animating SELECT AVG(price):
   row store touches every cell, column store only the price column.
   ===================================================================== */

const COLS = ["id", "date", "customer", "price", "qty"];
const N_ROWS = 8;
const PRICE_IDX = 3;
const CELL_W = 62, CELL_H = 26, GAP = 3;

function buildGrid(orientation) {
  // orientation: "row" | "column" — only affects the caption; cells identical
  const width = COLS.length * (CELL_W + GAP) + 10;
  const height = (N_ROWS + 1) * (CELL_H + GAP) + 34;
  const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, width, height });

  svg.appendChild(svgText(
    orientation === "row" ? "Row store (e.g. SQLite, Postgres)" : "Column store (DuckDB)",
    { x: width / 2, y: 16, "text-anchor": "middle", class: "svg-title" }
  ));

  const cells = []; // cells[r][c]
  for (let c = 0; c < COLS.length; c++) {
    svg.appendChild(svgText(COLS[c], {
      x: c * (CELL_W + GAP) + 5 + CELL_W / 2,
      y: 40,
      "text-anchor": "middle",
      class: "svg-label",
      "font-weight": c === PRICE_IDX ? "700" : "400",
    }));
  }
  for (let r = 0; r < N_ROWS; r++) {
    cells.push([]);
    for (let c = 0; c < COLS.length; c++) {
      const rect = svgEl("rect", {
        x: c * (CELL_W + GAP) + 5,
        y: (r + 1) * (CELL_H + GAP) + 26,
        width: CELL_W,
        height: CELL_H,
        rx: 4,
        fill: "#1e2230",
        stroke: "#2a2f40",
      });
      svg.appendChild(rect);
      cells[r].push(rect);
    }
  }
  return { svg, cells };
}

function resetGrid(cells) {
  for (const row of cells) for (const rect of row) {
    rect.setAttribute("fill", "#1e2230");
    rect.setAttribute("stroke", "#2a2f40");
  }
}

export function initRowVsColumn({ rowMount, colMount, runBtn, resetBtn, rowCounter, colCounter, speed }) {
  const rowGrid = buildGrid("row");
  const colGrid = buildGrid("column");
  rowMount.appendChild(rowGrid.svg);
  colMount.appendChild(colGrid.svg);

  let timer = null;

  function reset() {
    clearInterval(timer);
    timer = null;
    resetGrid(rowGrid.cells);
    resetGrid(colGrid.cells);
    rowCounter.textContent = "0";
    colCounter.textContent = "0";
    runBtn.disabled = false;
  }

  function run() {
    reset();
    runBtn.disabled = true;
    let tick = 0;
    let rowRead = 0, colRead = 0;
    const totalTicks = N_ROWS * COLS.length; // row store reads one cell per tick
    const interval = Number(speed.value);

    timer = setInterval(() => {
      // Row store: sweeps row by row, every cell (wasted reads in red)
      const r = Math.floor(tick / COLS.length);
      const c = tick % COLS.length;
      const rect = rowGrid.cells[r][c];
      rect.setAttribute("fill", c === PRICE_IDX ? "rgba(74,222,128,.35)" : "rgba(248,113,113,.30)");
      rect.setAttribute("stroke", c === PRICE_IDX ? "#4ade80" : "#f87171");
      rowRead++;
      rowCounter.textContent = String(rowRead);

      // Column store: touches only the price column, one cell per row sweep
      if (c === 0 && r < N_ROWS) {
        const priceRect = colGrid.cells[r][PRICE_IDX];
        priceRect.setAttribute("fill", "rgba(74,222,128,.35)");
        priceRect.setAttribute("stroke", "#4ade80");
        colRead++;
        colCounter.textContent = String(colRead);
      }

      tick++;
      if (tick >= totalTicks) {
        clearInterval(timer);
        timer = null;
        runBtn.disabled = false;
      }
    }, interval);
  }

  runBtn.addEventListener("click", run);
  resetBtn.addEventListener("click", reset);
}

/* =====================================================================
   2. In-process vs client-server architecture
   Animated dot crossing the network boundary vs a short internal hop.
   ===================================================================== */

export function initArchitecture(mount) {
  const W = 860, H = 270;
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%" });

  const box = (x, y, w, h, fill, stroke) =>
    svgEl("rect", { x, y, width: w, height: h, rx: 10, fill, stroke, "stroke-width": 1.5 });
  const label = (str, x, y, cls = "svg-title", anchor = "middle") =>
    svgText(str, { x, y, "text-anchor": anchor, class: cls });

  /* left: client-server */
  svg.appendChild(label("Client–server (PostgreSQL, MySQL)", 210, 24));
  svg.appendChild(box(30, 50, 150, 170, "#1e2230", "#5aa9ff"));
  svg.appendChild(label("Your app", 105, 78));
  svg.appendChild(box(55, 100, 100, 44, "#171a23", "#2a2f40"));
  svg.appendChild(label("SQL client", 105, 127, "svg-label"));
  svg.appendChild(box(55, 158, 100, 44, "#171a23", "#2a2f40"));
  svg.appendChild(label("serialize /", 105, 176, "svg-label"));
  svg.appendChild(label("deserialize", 105, 192, "svg-label"));

  // network boundary
  svg.appendChild(svgEl("line", { x1: 210, y1: 50, x2: 210, y2: 230, stroke: "#f87171", "stroke-dasharray": "6 5", "stroke-width": 1.5 }));
  svg.appendChild(label("network / IPC", 210, 248, "svg-label"));

  svg.appendChild(box(245, 50, 150, 170, "#1e2230", "#f87171"));
  svg.appendChild(label("DB server process", 320, 78, "svg-label"));
  svg.appendChild(label("PostgreSQL", 320, 100));
  svg.appendChild(box(270, 120, 100, 44, "#171a23", "#2a2f40"));
  svg.appendChild(label("parse / plan /", 320, 138, "svg-label"));
  svg.appendChild(label("execute", 320, 154, "svg-label"));
  svg.appendChild(box(270, 172, 100, 40, "#171a23", "#2a2f40"));
  svg.appendChild(label("storage", 320, 196, "svg-label"));

  // animated dot traveling across the boundary and back
  const path1 = svgEl("path", { id: "net-path", d: "M 160 122 L 265 142 L 160 122", fill: "none" });
  svg.appendChild(path1);
  const dot1 = svgEl("circle", { r: 6, fill: "#f87171" });
  const anim1 = svgEl("animateMotion", { dur: "2.4s", repeatCount: "indefinite" });
  anim1.appendChild(svgEl("mpath", { href: "#net-path" }));
  dot1.appendChild(anim1);
  svg.appendChild(dot1);

  /* right: in-process */
  svg.appendChild(label("In-process (DuckDB, SQLite)", 640, 24));
  svg.appendChild(box(490, 50, 300, 170, "#1e2230", "#ffd54a"));
  svg.appendChild(label("Your app — one process", 640, 78));
  svg.appendChild(box(515, 100, 110, 100, "#171a23", "#2a2f40"));
  svg.appendChild(label("your code", 570, 152, "svg-label"));
  svg.appendChild(box(655, 100, 110, 100, "#171a23", "#ffd54a"));
  svg.appendChild(label("DuckDB", 710, 130));
  svg.appendChild(label("(a library)", 710, 150, "svg-label"));
  svg.appendChild(label("same memory space", 640, 244, "svg-label"));

  const path2 = svgEl("path", { id: "call-path", d: "M 625 150 L 655 150 L 625 150", fill: "none" });
  svg.appendChild(path2);
  const dot2 = svgEl("circle", { r: 6, fill: "#4ade80" });
  const anim2 = svgEl("animateMotion", { dur: "0.5s", repeatCount: "indefinite" });
  anim2.appendChild(svgEl("mpath", { href: "#call-path" }));
  dot2.appendChild(anim2);
  svg.appendChild(dot2);

  mount.appendChild(svg);
}

/* =====================================================================
   3. Tuple-at-a-time vs vectorized execution
   Two pipelines Scan -> Filter -> Aggregate; left drips tuples with a
   call counter racking up, right pushes one 2048-row chunk per operator.
   ===================================================================== */

export function initVectorized({ mount, runBtn, resetBtn, tupleCounter, vectorCounter }) {
  const W = 760, H = 330;
  const OPS = ["Aggregate", "Filter", "Scan"]; // drawn top-down; data flows up
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%" });

  function pipeline(cx, title) {
    svg.appendChild(svgText(title, { x: cx, y: 22, "text-anchor": "middle", class: "svg-title" }));
    const boxes = [];
    OPS.forEach((op, i) => {
      const y = 46 + i * 92;
      svg.appendChild(svgEl("rect", { x: cx - 85, y, width: 170, height: 44, rx: 8, fill: "#1e2230", stroke: "#2a2f40", "stroke-width": 1.5 }));
      svg.appendChild(svgText(op, { x: cx, y: y + 27, "text-anchor": "middle", class: "svg-label", "font-size": "14" }));
      boxes.push(y);
      if (i < OPS.length - 1) {
        svg.appendChild(svgEl("line", { x1: cx, y1: y + 90, x2: cx, y2: y + 46, stroke: "#3a4055", "stroke-width": 2, "marker-end": "" }));
      }
    });
    return boxes; // y positions of the 3 operator boxes
  }

  const leftBoxes = pipeline(190, "Tuple-at-a-time (classic engines)");
  const rightBoxes = pipeline(570, "Vectorized (DuckDB): 2048 rows per call");

  // moving payloads
  const tuple = svgEl("rect", { x: 190 - 7, y: 300, width: 14, height: 14, rx: 3, fill: "#f87171", opacity: 0 });
  const chunk = svgEl("rect", { x: 570 - 60, y: 292, width: 120, height: 22, rx: 5, fill: "#4ade80", opacity: 0 });
  svg.appendChild(tuple);
  svg.appendChild(chunk);
  mount.appendChild(svg);

  const N_TUPLES = 12;      // stand-ins for 2048 rows
  let running = false;

  function reset() {
    running = false;
    tuple.setAttribute("opacity", 0);
    chunk.setAttribute("opacity", 0);
    tupleCounter.textContent = "0";
    vectorCounter.textContent = "0";
    runBtn.disabled = false;
  }

  function animateAlong(el, yStart, yEnd, ms) {
    return new Promise((resolve) => {
      const t0 = performance.now();
      el.setAttribute("opacity", 1);
      function frame(t) {
        if (!running) return resolve();
        const p = Math.min((t - t0) / ms, 1);
        el.setAttribute("y", yStart + (yEnd - yStart) * p);
        if (p < 1) requestAnimationFrame(frame);
        else resolve();
      }
      requestAnimationFrame(frame);
    });
  }

  async function run() {
    reset();
    running = true;
    runBtn.disabled = true;
    let tupleCalls = 0, vectorCalls = 0;

    // Right pipeline: one chunk, one call per operator — finishes fast.
    const chunkRun = (async () => {
      let y = 292;
      for (let i = OPS.length - 1; i >= 0; i--) {
        const target = rightBoxes[i] + 11;
        await animateAlong(chunk, y, target, 420);
        if (!running) return;
        vectorCalls++;
        vectorCounter.textContent = String(vectorCalls);
        y = target;
      }
      chunk.setAttribute("opacity", 0.35);
    })();

    // Left pipeline: every tuple crawls through every operator.
    const tupleRun = (async () => {
      for (let n = 0; n < N_TUPLES && running; n++) {
        let y = 300;
        for (let i = OPS.length - 1; i >= 0 && running; i--) {
          const target = leftBoxes[i] + 15;
          await animateAlong(tuple, y, target, 130);
          tupleCalls++;
          tupleCounter.textContent = `${tupleCalls}  (×170 for 2048 rows)`;
          y = target;
        }
      }
      tuple.setAttribute("opacity", 0);
    })();

    await Promise.all([chunkRun, tupleRun]);
    if (running) runBtn.disabled = false;
  }

  runBtn.addEventListener("click", run);
  resetBtn.addEventListener("click", reset);
}

/* =====================================================================
   4. 2x2 quadrant: in-process <-> client-server  ×  OLTP <-> OLAP
   ===================================================================== */

export function initQuadrant(mount) {
  const W = 640, H = 420;
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%" });

  const cx = W / 2, cy = H / 2 + 10;

  // axes
  svg.appendChild(svgEl("line", { x1: 60, y1: cy, x2: W - 60, y2: cy, stroke: "#3a4055", "stroke-width": 1.5 }));
  svg.appendChild(svgEl("line", { x1: cx, y1: 46, x2: cx, y2: H - 36, stroke: "#3a4055", "stroke-width": 1.5 }));

  svg.appendChild(svgText("OLTP  (transactions)", { x: 66, y: cy - 10, class: "svg-label", "text-anchor": "start" }));
  svg.appendChild(svgText("OLAP  (analytics)", { x: W - 66, y: cy - 10, class: "svg-label", "text-anchor": "end" }));
  svg.appendChild(svgText("in-process", { x: cx, y: 38, class: "svg-label", "text-anchor": "middle" }));
  svg.appendChild(svgText("client–server", { x: cx, y: H - 14, class: "svg-label", "text-anchor": "middle" }));

  const place = (name, x, y, highlight = false) => {
    const g = svgEl("g");
    const w = name.length * 8.4 + 30;
    g.appendChild(svgEl("rect", {
      x: x - w / 2, y: y - 17, width: w, height: 34, rx: 17,
      fill: highlight ? "rgba(255,213,74,.15)" : "#1e2230",
      stroke: highlight ? "#ffd54a" : "#2a2f40",
      "stroke-width": highlight ? 2 : 1.5,
    }));
    g.appendChild(svgText(name, {
      x, y: y + 5, "text-anchor": "middle",
      fill: highlight ? "#ffd54a" : "#e6e8ef",
      "font-size": "14", "font-weight": highlight ? "700" : "400",
    }));
    svg.appendChild(g);
  };

  place("SQLite", cx - 140, cy - 90);
  place("PostgreSQL / MySQL", cx - 150, cy + 90);
  place("Snowflake / BigQuery", cx + 155, cy + 90);
  place("DuckDB 🦆", cx + 140, cy - 90, true);

  svg.appendChild(svgText("← this corner was empty until 2019", {
    x: cx + 140, y: cy - 52, "text-anchor": "middle", class: "svg-label", fill: "#ffd54a",
  }));

  mount.appendChild(svg);
}
