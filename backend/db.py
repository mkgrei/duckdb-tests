"""DuckDB connection management for the playground.

A single file-backed connection is shared by the whole app. DuckDB is an
in-process library — this module IS the "database server". A threading.Lock
serializes access because FastAPI may handle requests on multiple threads;
that is plenty for a single-user teaching tool.
"""

import datetime
import decimal
import threading
import time
from pathlib import Path

import duckdb

from . import sample_data

DB_FILE = sample_data.DATA_DIR / "playground.duckdb"
MAX_ROWS = 500

_lock = threading.Lock()
_con: duckdb.DuckDBPyConnection | None = None


def _jsonable(value):
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    return value


def _seed(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        f"CREATE OR REPLACE TABLE sales AS SELECT * FROM read_csv_auto('{sample_data.SALES_CSV}')"
    )


def startup() -> None:
    global _con
    with _lock:
        sample_data.generate()
        DB_FILE.parent.mkdir(exist_ok=True)
        _con = duckdb.connect(str(DB_FILE))
        _seed(_con)


def shutdown() -> None:
    global _con
    with _lock:
        if _con is not None:
            _con.close()
            _con = None


def reset() -> None:
    """Close, delete the database file, reconnect and reseed."""
    global _con
    with _lock:
        if _con is not None:
            _con.close()
        DB_FILE.unlink(missing_ok=True)
        Path(str(DB_FILE) + ".wal").unlink(missing_ok=True)
        _con = duckdb.connect(str(DB_FILE))
        _seed(_con)


def run_sql(sql: str) -> dict:
    """Execute SQL (may contain multiple statements) and shape the result.

    Raises duckdb.Error on bad SQL — callers surface the message verbatim,
    because DuckDB's error messages are themselves good teaching material.
    """
    with _lock:
        assert _con is not None, "database not started"
        started = time.perf_counter()
        cursor = _con.execute(sql)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchall() if columns else []
        elapsed_ms = (time.perf_counter() - started) * 1000

    truncated = len(rows) > MAX_ROWS
    rows = rows[:MAX_ROWS]
    return {
        "columns": columns,
        "rows": [[_jsonable(v) for v in row] for row in rows],
        "row_count": len(rows),
        "elapsed_ms": round(elapsed_ms, 2),
        "truncated": truncated,
    }


def explain(sql: str, analyze: bool = False) -> str:
    prefix = "EXPLAIN ANALYZE " if analyze else "EXPLAIN "
    stripped = sql.strip()
    if stripped.upper().startswith("EXPLAIN"):
        stripped = stripped[len("EXPLAIN"):].lstrip()
    with _lock:
        assert _con is not None, "database not started"
        rows = _con.execute(prefix + stripped).fetchall()
    return "\n".join(part for row in rows for part in row[1:])


def state() -> dict:
    """Snapshot of the database: tables, schemas, row counts, file size."""
    with _lock:
        assert _con is not None, "database not started"
        tables = [
            r[0]
            for r in _con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main' ORDER BY table_name"
            ).fetchall()
        ]
        out = []
        for name in tables:
            columns = _con.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = 'main' AND table_name = ? ORDER BY ordinal_position",
                [name],
            ).fetchall()
            row_count = _con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
            out.append(
                {
                    "name": name,
                    "row_count": row_count,
                    "columns": [{"name": c, "type": t} for c, t in columns],
                }
            )
    return {
        "tables": out,
        "db_file_bytes": DB_FILE.stat().st_size if DB_FILE.exists() else 0,
        "duckdb_version": duckdb.__version__,
    }
