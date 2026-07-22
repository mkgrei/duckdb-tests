import { initRowVsColumn, initArchitecture, initVectorized, initQuadrant } from "./diagrams.js";

initQuadrant(document.getElementById("quadrant-mount"));

initRowVsColumn({
  rowMount: document.getElementById("rvc-row-mount"),
  colMount: document.getElementById("rvc-col-mount"),
  runBtn: document.getElementById("rvc-run"),
  resetBtn: document.getElementById("rvc-reset"),
  rowCounter: document.getElementById("rvc-row-counter"),
  colCounter: document.getElementById("rvc-col-counter"),
  speed: document.getElementById("rvc-speed"),
});

initArchitecture(document.getElementById("arch-mount"));

initVectorized({
  mount: document.getElementById("vec-mount"),
  runBtn: document.getElementById("vec-run"),
  resetBtn: document.getElementById("vec-reset"),
  tupleCounter: document.getElementById("vec-tuple-counter"),
  vectorCounter: document.getElementById("vec-vector-counter"),
});

/* comparison table: click a column header to highlight that column */
const table = document.getElementById("compare-table");
table.querySelectorAll("th[data-col]").forEach((th) => {
  th.addEventListener("click", () => {
    const col = Number(th.dataset.col);
    const active = th.classList.contains("hl");
    table.querySelectorAll(".hl").forEach((el) => el.classList.remove("hl"));
    if (active) return;
    th.classList.add("hl");
    table.querySelectorAll("tbody tr").forEach((tr) => tr.children[col].classList.add("hl"));
  });
});
