"""DuckDB Explained — educational site + live playground.

Run with:  python app.py   (serves on http://127.0.0.1:8000)
"""

from contextlib import asynccontextmanager
from pathlib import Path

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import actions, db

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


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/playground")
def playground():
    return FileResponse(STATIC / "playground.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
