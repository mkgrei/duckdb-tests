"""Tests for backend.s3_logs — the S3/EKS audit log integration."""

from datetime import datetime, timedelta

import pytest

from backend import s3_logs
from backend.s3_logs import AIQueryTranslator, LokiQueryParser


class TestLokiQueryParser:
    def test_parse_time_range_units(self):
        assert LokiQueryParser.parse_time_range("30s") == timedelta(seconds=30)
        assert LokiQueryParser.parse_time_range("15m") == timedelta(minutes=15)
        assert LokiQueryParser.parse_time_range("1h") == timedelta(hours=1)
        assert LokiQueryParser.parse_time_range("7d") == timedelta(days=7)

    def test_parse_time_range_invalid_defaults_to_24h(self):
        assert LokiQueryParser.parse_time_range("nonsense") == timedelta(hours=24)
        assert LokiQueryParser.parse_time_range("") == timedelta(hours=24)

    def test_parse_logql_labels(self):
        filters = LokiQueryParser.parse_logql('{namespace="kube-system",verb="get"}')
        assert filters == {"namespace": "kube-system", "verb": "get"}

    def test_parse_logql_line_filters(self):
        filters = LokiQueryParser.parse_logql('{verb="create"} |= "error" != "success"')
        assert filters["verb"] == "create"
        assert filters["_includes"] == ["error"]
        assert filters["_excludes"] == ["success"]

    def test_parse_logql_no_labels(self):
        assert LokiQueryParser.parse_logql("plain text") == {}


class TestAIQueryTranslator:
    def test_failed_creations(self):
        t = AIQueryTranslator.translate_question("Show me all failed pod creations")
        assert t["filters"]["verb"] == "create"
        assert t["filters"]["responseStatus_code"] == 403

    def test_namespace_and_user_extraction(self):
        t = AIQueryTranslator.translate_question(
            "What did user john do in namespace production?"
        )
        assert t["filters"]["objectRef_namespace"] == "production"
        assert t["filters"]["user_username"] == "john"

    def test_delete_verb(self):
        t = AIQueryTranslator.translate_question("Find all delete operations")
        assert t["filters"]["verb"] == "delete"

    def test_time_range_passthrough(self):
        t = AIQueryTranslator.translate_question("anything", time_range="1h")
        assert t["time_range"] == "1h"


class TestBuildEksQuery:
    def test_no_filters(self, monkeypatch):
        monkeypatch.setattr(s3_logs, "S3_BUCKET", "bucket")
        sql, params = s3_logs.build_eks_query(limit=50)
        assert "read_json_auto('s3://bucket/eks-audit-logs/*.json')" in sql
        assert "WHERE 1=1" in sql
        assert "LIMIT 50" in sql
        assert params == []

    def test_filters_and_times_are_parameterized(self, monkeypatch):
        monkeypatch.setattr(s3_logs, "S3_BUCKET", "bucket")
        start = datetime(2026, 1, 1)
        sql, params = s3_logs.build_eks_query(
            start_time=start,
            filters={"verb": "create", "objectRef_namespace": "prod"},
        )
        assert "timestamp >= ?" in sql
        assert "verb = ?" in sql
        assert "objectRef_namespace = ?" in sql
        assert params == [start.isoformat(), "create", "prod"]
        # values never appear in the SQL text itself
        assert "create" not in sql.split("read_json_auto")[1].split("WHERE")[1]

    def test_unknown_filter_key_rejected(self, monkeypatch):
        monkeypatch.setattr(s3_logs, "S3_BUCKET", "bucket")
        with pytest.raises(ValueError, match="unsupported filter"):
            s3_logs.build_eks_query(filters={"1=1; DROP TABLE x; --": "y"})

    def test_limit_is_coerced_to_int(self, monkeypatch):
        monkeypatch.setattr(s3_logs, "S3_BUCKET", "bucket")
        with pytest.raises((ValueError, TypeError)):
            s3_logs.build_eks_query(limit="10; DROP TABLE x")


class TestConfiguration:
    def test_query_without_bucket_raises(self, monkeypatch):
        monkeypatch.setattr(s3_logs, "S3_BUCKET", None)
        with pytest.raises(s3_logs.S3NotConfigured):
            s3_logs.query_eks_logs()

    def test_status_shape(self):
        s = s3_logs.status()
        assert set(s) == {
            "configured",
            "bucket",
            "prefix",
            "region",
            "credentials_set",
            "extensions_error",
        }


class TestHttpEndpoints:
    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient

        import app as app_module

        with TestClient(app_module.app) as client:
            yield client

    def test_s3_status_endpoint(self, client):
        r = client.get("/api/s3/status")
        assert r.status_code == 200
        assert "configured" in r.json()

    def test_s3_schema_endpoint(self, client):
        r = client.get("/api/s3/schema")
        assert r.status_code == 200
        assert "verb" in r.json()["fields"]

    def test_s3_query_unconfigured_returns_503(self, client, monkeypatch):
        monkeypatch.setattr(s3_logs, "S3_BUCKET", None)
        r = client.get("/api/s3/query?verb=create")
        assert r.status_code == 503
        assert "S3_BUCKET" in r.json()["detail"]

    def test_loki_endpoint_unconfigured_returns_503(self, client, monkeypatch):
        monkeypatch.setattr(s3_logs, "S3_BUCKET", None)
        r = client.post(
            "/api/s3/loki", json={"query": '{verb="get"}', "time_range": "1h"}
        )
        assert r.status_code == 503

    def test_ai_endpoint_unconfigured_returns_503(self, client, monkeypatch):
        monkeypatch.setattr(s3_logs, "S3_BUCKET", None)
        r = client.post("/api/s3/ai", json={"question": "failed pod creations"})
        assert r.status_code == 503

    def test_bad_timestamp_returns_400(self, client, monkeypatch):
        monkeypatch.setattr(s3_logs, "S3_BUCKET", "bucket")
        r = client.get("/api/s3/query?start_time=not-a-date")
        assert r.status_code == 400

    def test_existing_endpoints_still_work(self, client):
        r = client.post("/api/query", json={"sql": "SELECT 1 AS one"})
        assert r.status_code == 200
        assert r.json()["rows"] == [[1]]
