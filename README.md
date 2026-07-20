# 🦆 DuckDB Explained

An educational web app for understanding **how DuckDB works** — not just how to
call it. Two halves:

1. **Learn** (`/`) — the ideas behind DuckDB, told with interactive SVG
   animations:
   - the 2×2 quadrant (in-process ↔ client–server × OLTP ↔ OLAP) showing the
     gap DuckDB was born to fill
   - an animated **row-store vs column-store** scan of `SELECT AVG(price)`
     (watch the cells-read counters diverge: 40 vs 8)
   - **in-process vs client–server** architecture, with the network round-trip
     animated away
   - **tuple-at-a-time vs vectorized execution** pipelines with live
     operator-call counters
   - an interactive comparison table (SQLite / PostgreSQL / pandas / DuckDB)

2. **Playground** (`/playground`) — a toy app backed by a **real DuckDB
   database** on the server. An 8-step guided tour runs typical DuckDB actions
   (ingest a CSV, query Parquet in place, OLAP aggregation, window functions,
   join a table against a raw file, UPDATE/DELETE, CTAS, EXPLAIN) while a live
   **DB State panel** shows tables, schemas, and row counts changing after
   every action. There's also a free-form SQL editor with Run / Explain /
   Explain Analyze, and a reset button that rebuilds the database.

## Run it

```bash
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:8000
```

Sample data (`data/sales.csv`, ~5,000 rows, and `data/products.parquet`) is
generated automatically on first startup; the DuckDB database file lives at
`data/playground.duckdb`.

## Architecture

```
app.py                  FastAPI app — serves the API and the static frontend
backend/db.py           single shared DuckDB connection, run_sql/explain/state/reset
backend/actions.py      the 8-step guided tour registry (SQL + explanations)
backend/sample_data.py  idempotent CSV/Parquet generation (Parquet written by DuckDB itself)
static/                 vanilla HTML/CSS/JS — no build step, no frameworks
  js/diagrams.js        SVG diagram builders + animations
  js/playground.js      tour runner, SQL editor, live DB state panel
```

### API

| Endpoint | Purpose |
|---|---|
| `POST /api/query` | run SQL → columns/rows/elapsed_ms (errors surface DuckDB's message verbatim) |
| `POST /api/explain` | `EXPLAIN` / `EXPLAIN ANALYZE` plan text |
| `GET /api/state` | tables, schemas, row counts, DB file size |
| `GET /api/actions` | the guided tour registry |
| `POST /api/actions/{id}` | execute one tour step, returns result + fresh state |
| `POST /api/reset` | delete the DB file, reconnect, reseed |

Interactive API docs (FastAPI) at `/docs`.
