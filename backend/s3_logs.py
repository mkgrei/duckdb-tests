"""EKS audit log analysis over S3, running on the app's shared DuckDB connection.

Ported from samples/python/eks-audit-s3-analysis and integrated into the main
server: instead of a separate in-memory engine, the httpfs/json extensions and
S3 credentials are applied to the playground's connection at startup, so both
the guided-tour SQL editor and these endpoints can read s3:// paths.

Configuration comes from the environment (see .env.example):
  AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET, S3_PREFIX
"""

import os
import re
from datetime import datetime, timedelta, timezone

import duckdb

try:  # optional: pick up a local .env if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX", "eks-audit-logs/")

# Set by configure_connection(); surfaced through status().
_extensions_error: str | None = None

AUDIT_LOG_SCHEMA = {
    "description": "EKS Kubernetes Audit Log Schema",
    "fields": {
        "timestamp": "ISO8601 timestamp of the event",
        "level": "Audit level (Metadata, Request, RequestResponse)",
        "auditID": "Unique audit event ID",
        "stage": "Stage of the request (ResponseComplete, RequestReceived, etc.)",
        "requestURI": "The request URI",
        "verb": "Kubernetes API verb (get, list, create, update, delete, patch, watch)",
        "user": {
            "username": "Username of the user making the request",
            "uid": "User ID",
            "groups": "List of user groups",
        },
        "sourceIPs": "List of source IP addresses",
        "userAgent": "User agent string",
        "objectRef": {
            "resource": "Resource type (pods, services, deployments, etc.)",
            "namespace": "Kubernetes namespace",
            "name": "Resource name",
            "apiVersion": "API version",
        },
        "responseStatus": {
            "code": "HTTP response code",
            "status": "Response status",
        },
        "requestReceivedTimestamp": "When the request was received",
        "stageTimestamp": "Timestamp for this stage",
        "annotations": "Additional annotations",
    },
}

# Filter keys accepted by query_eks_logs — everything else is rejected so the
# WHERE clause can only reference known audit-log columns.
ALLOWED_FILTER_COLUMNS = {
    "verb",
    "level",
    "stage",
    "auditID",
    "requestURI",
    "userAgent",
    "objectRef_namespace",
    "objectRef_resource",
    "objectRef_name",
    "user_username",
    "responseStatus_code",
}


def configure_connection(con: duckdb.DuckDBPyConnection) -> None:
    """Load httpfs/json and apply S3 credentials to a DuckDB connection.

    Extension installation needs network access on first run; failure is
    recorded rather than raised so the rest of the app still starts.
    """
    global _extensions_error
    try:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute("INSTALL json; LOAD json;")
        _extensions_error = None
    except duckdb.Error as e:
        _extensions_error = str(e)
        return

    con.execute("SET s3_region = ?", [AWS_REGION])
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        con.execute("SET s3_access_key_id = ?", [AWS_ACCESS_KEY_ID])
        con.execute("SET s3_secret_access_key = ?", [AWS_SECRET_ACCESS_KEY])


def is_configured() -> bool:
    return bool(S3_BUCKET) and _extensions_error is None


def status() -> dict:
    return {
        "configured": is_configured(),
        "bucket": S3_BUCKET,
        "prefix": S3_PREFIX,
        "region": AWS_REGION,
        "credentials_set": bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY),
        "extensions_error": _extensions_error,
    }


def s3_glob() -> str:
    """The s3:// glob the audit-log queries read from."""
    return f"s3://{S3_BUCKET}/{S3_PREFIX}*.json"


class S3NotConfigured(RuntimeError):
    pass


def _require_configured() -> None:
    if not S3_BUCKET:
        raise S3NotConfigured(
            "S3_BUCKET is not set — configure the environment (see .env.example)"
        )
    if _extensions_error is not None:
        raise S3NotConfigured(
            f"DuckDB httpfs/json extensions unavailable: {_extensions_error}"
        )


def build_eks_query(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    filters: dict | None = None,
    limit: int = 1000,
) -> tuple[str, list]:
    """Build the parameterized SQL for an audit-log query.

    Returns (sql, params). Filter values and timestamps are bound as
    parameters; filter keys must be in ALLOWED_FILTER_COLUMNS.
    """
    where, params = [], []
    if start_time:
        where.append("timestamp >= ?")
        params.append(start_time.isoformat())
    if end_time:
        where.append("timestamp <= ?")
        params.append(end_time.isoformat())
    for key, value in (filters or {}).items():
        if key not in ALLOWED_FILTER_COLUMNS:
            raise ValueError(f"unsupported filter: {key}")
        where.append(f"{key} = ?")
        params.append(value)

    sql = (
        f"SELECT * FROM read_json_auto('{s3_glob()}')\n"
        f"WHERE {' AND '.join(where) if where else '1=1'}\n"
        f"ORDER BY timestamp DESC\nLIMIT {int(limit)}"
    )
    return sql, params


def query_eks_logs(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    filters: dict | None = None,
    limit: int = 1000,
) -> list[dict]:
    """Query EKS audit logs from S3; returns rows as a list of dicts."""
    _require_configured()
    from . import db  # imported lazily to avoid a circular import at load time

    sql, params = build_eks_query(start_time, end_time, filters, limit)
    result = db.run_sql(sql, params=params, max_rows=limit)
    return [dict(zip(result["columns"], row)) for row in result["rows"]]


class LokiQueryParser:
    """Parse Grafana Loki (LogQL)-style queries into filters."""

    @staticmethod
    def parse_time_range(time_str: str) -> timedelta:
        """Parse a time range string like '30s', '15m', '1h', '7d'."""
        match = re.match(r"(\d+)([smhd])", time_str or "")
        if not match:
            return timedelta(hours=24)
        value, unit = int(match.group(1)), match.group(2)
        return {
            "s": timedelta(seconds=value),
            "m": timedelta(minutes=value),
            "h": timedelta(hours=value),
            "d": timedelta(days=value),
        }[unit]

    @staticmethod
    def parse_logql(query: str) -> dict:
        """Extract filters from a LogQL-style query.

        Example: {namespace="kube-system",verb="get"} |= "error" != "success"
        Label filters land as key/value pairs; line filters land under the
        special keys _includes / _excludes.
        """
        filters = {}
        match = re.search(r"\{([^}]+)\}", query)
        if match:
            for key, value in re.findall(r'(\w+)="([^"]+)"', match.group(1)):
                filters[key] = value

        includes = re.findall(r'\|=\s*"([^"]+)"', query)
        excludes = re.findall(r'!=\s*"([^"]+)"', query)
        if includes:
            filters["_includes"] = includes
        if excludes:
            filters["_excludes"] = excludes
        return filters


# LogQL label names -> audit-log column names.
LOKI_LABEL_MAP = {
    "namespace": "objectRef_namespace",
    "resource": "objectRef_resource",
    "name": "objectRef_name",
    "user": "user_username",
}


def loki_query(query: str, time_range: str = "24h", limit: int = 1000) -> dict:
    """Run a LogQL-style query against the audit logs."""
    raw = LokiQueryParser.parse_logql(query)
    includes = raw.pop("_includes", [])
    excludes = raw.pop("_excludes", [])
    filters = {LOKI_LABEL_MAP.get(k, k): v for k, v in raw.items()}

    delta = LokiQueryParser.parse_time_range(time_range)
    end_time = datetime.now(timezone.utc).replace(tzinfo=None)
    results = query_eks_logs(
        start_time=end_time - delta, end_time=end_time, filters=filters, limit=limit
    )

    if includes or excludes:
        import json as _json

        def keep(row: dict) -> bool:
            text = _json.dumps(row, default=str).lower()
            if includes and not any(t.lower() in text for t in includes):
                return False
            if excludes and any(t.lower() in text for t in excludes):
                return False
            return True

        results = [r for r in results if keep(r)]

    return {
        "query": query,
        "time_range": time_range,
        "count": len(results),
        "results": results,
    }


class AIQueryTranslator:
    """Rule-based translation of natural-language questions into filters.

    A deliberately simple stand-in — in production you'd hand this to an LLM.
    """

    @staticmethod
    def translate_question(question: str, time_range: str = "24h") -> dict:
        q = question.lower()
        filters = {}

        if "failed" in q or "error" in q:
            filters["verb"] = "create"
            filters["responseStatus_code"] = 403

        if "create" in q:
            filters["verb"] = "create"
        elif "delete" in q:
            filters["verb"] = "delete"
        elif "update" in q:
            filters["verb"] = "update"
        elif "get" in q or "read" in q:
            filters["verb"] = "get"

        namespace_match = re.search(r"namespace\s+(\S+)", q)
        if namespace_match:
            filters["objectRef_namespace"] = namespace_match.group(1).rstrip("?.,!")

        user_match = re.search(r"user\s+(\S+)", q)
        if user_match:
            filters["user_username"] = user_match.group(1).rstrip("?.,!")

        return {"filters": filters, "time_range": time_range}


def ai_query(question: str, time_range: str = "24h", limit: int = 1000) -> dict:
    """Answer a natural-language question about the audit logs."""
    translation = AIQueryTranslator.translate_question(question, time_range)
    delta = LokiQueryParser.parse_time_range(translation["time_range"])
    end_time = datetime.now(timezone.utc).replace(tzinfo=None)
    results = query_eks_logs(
        start_time=end_time - delta,
        end_time=end_time,
        filters=translation["filters"],
        limit=limit,
    )

    summary = {
        "total_events": len(results),
        "unique_verbs": sorted({r.get("verb") or "unknown" for r in results}),
        "unique_namespaces": sorted(
            {r.get("objectRef_namespace") or "unknown" for r in results}
        ),
        "unique_users": sorted({r.get("user_username") or "unknown" for r in results}),
    }
    return {
        "question": question,
        "time_range": time_range,
        "translation": translation,
        "summary": summary,
        "count": len(results),
        "results": results[:100],
    }
