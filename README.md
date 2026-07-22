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

3. **S3 audit log analysis** (`/api/s3/*`) — the EKS audit log sample
   (`samples/python/eks-audit-s3-analysis`) integrated into the same server.
   DuckDB's `httpfs` extension is loaded on the shared connection with S3
   credentials from the environment, so `s3://` paths work everywhere —
   including the free-form SQL editor — plus structured endpoints for
   filtered, Loki-style, and natural-language queries over EKS audit logs.

## Run it

```bash
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:8000
```

Sample data (`data/sales.csv`, ~5,000 rows, and `data/products.parquet`) is
generated automatically on first startup; the DuckDB database file lives at
`data/playground.duckdb`.

To enable the S3 audit-log endpoints, set the AWS/S3 environment variables
(copy `.env.example` and fill it in — a local `.env` is picked up
automatically if `python-dotenv` is installed). Without `S3_BUCKET` the
`/api/s3/*` query endpoints return 503 and everything else works as before.

## Architecture

```
app.py                  FastAPI app — serves the API and the static frontend
backend/db.py           single shared DuckDB connection, run_sql/explain/state/reset
backend/actions.py      the 8-step guided tour registry (SQL + explanations)
backend/s3_logs.py      S3/EKS audit log analysis: httpfs+S3 setup, LogQL & NL query translation
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
| `GET /api/s3/status` | S3 configuration status (bucket, region, extension availability) |
| `GET /api/s3/schema` | EKS audit log schema description |
| `GET /api/s3/query` | filtered audit-log query (`?verb=create&namespace=prod&limit=50`) |
| `POST /api/s3/loki` | Grafana Loki-style query (`{"query": "{verb=\"create\"}", "time_range": "1h"}`) |
| `POST /api/s3/ai` | natural-language query (`{"question": "failed pod creations", "time_range": "24h"}`) |

Interactive API docs (FastAPI) at `/docs`.

Run the tests with `pip install pytest httpx && python -m pytest tests/`.
