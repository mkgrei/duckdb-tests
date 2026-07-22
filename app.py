"""DuckDB Explained — educational site + live playground.

Run with:  python app.py [--host HOST] [--port PORT]
Defaults to http://127.0.0.1:8000; $HOST / $PORT env vars are also honored.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import actions, db, s3_logs

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.startup()
    yield
    db.shutdown()


app = FastAPI(title="DuckDB Explained", lifespan=lifespan)


class SqlRequest(BaseModel):
    sql: str


class ExplainRequest(BaseModel):
    sql: str
    analyze: bool = False


class LokiQueryRequest(BaseModel):
    query: str
    time_range: str = "24h"
    limit: int = 1000


class AIQueryRequest(BaseModel):
    question: str
    time_range: str = "24h"


@app.post("/api/query")
def query(req: SqlRequest):
    try:
        return db.run_sql(req.sql)
    except duckdb.Error as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/explain")
def explain(req: ExplainRequest):
    try:
        return {"plan": db.explain(req.sql, analyze=req.analyze)}
    except duckdb.Error as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/state")
def state():
    return db.state()


@app.get("/api/actions")
def list_actions():
    return {"actions": actions.ACTIONS}


@app.post("/api/actions/{action_id}")
def run_action(action_id: str):
    action = actions.BY_ID.get(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"unknown action: {action_id}")
    try:
        result = db.run_sql(action["sql"])
    except duckdb.Error as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"action": action, "result": result, "state": db.state()}


@app.post("/api/reset")
def reset():
    db.reset()
    return {"status": "reset", "state": db.state()}


# --- S3 / EKS audit log analysis ------------------------------------------
# The shared connection has httpfs loaded and S3 credentials applied (when
# configured), so the free-form /api/query endpoint can also read s3:// paths
# directly. The endpoints below add the structured EKS-audit-log interface.


def _s3_errors(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except s3_logs.S3NotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except duckdb.Error as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/s3/status")
def s3_status():
    return s3_logs.status()


@app.get("/api/s3/schema")
def s3_schema():
    return s3_logs.AUDIT_LOG_SCHEMA


@app.get("/api/s3/query")
def s3_query(
    start_time: str | None = None,
    end_time: str | None = None,
    verb: str | None = None,
    namespace: str | None = None,
    user: str | None = None,
    limit: int = 100,
):
    """Query EKS audit logs with basic filters.

    Example: /api/s3/query?verb=create&namespace=production&limit=50
    """
    filters = {}
    if verb:
        filters["verb"] = verb
    if namespace:
        filters["objectRef_namespace"] = namespace
    if user:
        filters["user_username"] = user

    try:
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"bad timestamp: {e}")

    results = _s3_errors(
        s3_logs.query_eks_logs,
        start_time=start_dt,
        end_time=end_dt,
        filters=filters,
        limit=max(1, min(limit, 10000)),
    )
    return {"status": "success", "count": len(results), "results": results}


@app.post("/api/s3/loki")
def s3_loki(req: LokiQueryRequest):
    """Grafana Loki-style query, e.g. {namespace="kube-system",verb="create"}."""
    return _s3_errors(s3_logs.loki_query, req.query, req.time_range, req.limit)


@app.post("/api/s3/ai")
def s3_ai(req: AIQueryRequest):
    """Natural-language query over the audit logs (rule-based translation)."""
    return _s3_errors(s3_logs.ai_query, req.question, req.time_range)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/playground")
def playground():
    return FileResponse(STATIC / "playground.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    import argparse
    import os

    import uvicorn

    parser = argparse.ArgumentParser(description="DuckDB Explained server")
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "127.0.0.1"),
        help="bind address (default: $HOST or 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="port to listen on (default: $PORT or 8000)",
    )
    cli = parser.parse_args()

    uvicorn.run(app, host=cli.host, port=cli.port)
