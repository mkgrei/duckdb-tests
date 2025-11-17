"""
Pytest configuration and shared fixtures for EKS Audit Log Analyzer tests
"""

import os
import json
import tempfile
from datetime import datetime, timedelta
from typing import List, Dict, Any

import pytest
import duckdb
from fastapi.testclient import TestClient


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_audit_log() -> Dict[str, Any]:
    """Single sample audit log entry"""
    return {
        "kind": "Event",
        "apiVersion": "audit.k8s.io/v1",
        "level": "RequestResponse",
        "auditID": "test-audit-id-001",
        "stage": "ResponseComplete",
        "requestURI": "/api/v1/namespaces/production/pods",
        "verb": "create",
        "user": {
            "username": "john.doe",
            "uid": "aws-iam-authenticator:123456789012:AIDAI23EXAMPLE",
            "groups": ["system:authenticated", "developers"]
        },
        "sourceIPs": ["10.0.1.100"],
        "userAgent": "kubectl/v1.28.0",
        "objectRef": {
            "resource": "pods",
            "namespace": "production",
            "name": "web-app-12345",
            "apiVersion": "v1"
        },
        "responseStatus": {
            "metadata": {},
            "code": 201
        },
        "requestReceivedTimestamp": "2024-01-15T10:30:00.123456Z",
        "stageTimestamp": "2024-01-15T10:30:00.234567Z",
        "timestamp": "2024-01-15T10:30:00.234567Z",
        "annotations": {
            "authorization.k8s.io/decision": "allow",
            "authorization.k8s.io/reason": "RBAC: allowed by RoleBinding"
        }
    }


@pytest.fixture
def sample_audit_logs() -> List[Dict[str, Any]]:
    """Multiple sample audit log entries"""
    base_time = datetime(2024, 1, 15, 10, 0, 0)

    logs = []

    # Successful pod creation
    logs.append({
        "timestamp": (base_time + timedelta(minutes=0)).isoformat() + "Z",
        "verb": "create",
        "objectRef_namespace": "production",
        "objectRef_resource": "pods",
        "objectRef_name": "web-app-001",
        "user_username": "john.doe",
        "responseStatus_code": 201,
        "sourceIPs": ["10.0.1.100"]
    })

    # Failed pod creation
    logs.append({
        "timestamp": (base_time + timedelta(minutes=5)).isoformat() + "Z",
        "verb": "create",
        "objectRef_namespace": "production",
        "objectRef_resource": "pods",
        "objectRef_name": "malicious-pod",
        "user_username": "unauthorized-user",
        "responseStatus_code": 403,
        "sourceIPs": ["10.0.3.200"]
    })

    # Pod deletion
    logs.append({
        "timestamp": (base_time + timedelta(minutes=10)).isoformat() + "Z",
        "verb": "delete",
        "objectRef_namespace": "production",
        "objectRef_resource": "pods",
        "objectRef_name": "web-app-001",
        "user_username": "jane.smith",
        "responseStatus_code": 200,
        "sourceIPs": ["10.0.1.101"]
    })

    # Secret update in kube-system
    logs.append({
        "timestamp": (base_time + timedelta(minutes=15)).isoformat() + "Z",
        "verb": "update",
        "objectRef_namespace": "kube-system",
        "objectRef_resource": "secrets",
        "objectRef_name": "aws-auth",
        "user_username": "system:admin",
        "responseStatus_code": 200,
        "sourceIPs": ["10.0.2.50"]
    })

    # List deployments in staging
    logs.append({
        "timestamp": (base_time + timedelta(minutes=20)).isoformat() + "Z",
        "verb": "list",
        "objectRef_namespace": "staging",
        "objectRef_resource": "deployments",
        "objectRef_name": "",
        "user_username": "monitoring-service",
        "responseStatus_code": 200,
        "sourceIPs": ["10.0.4.10"]
    })

    return logs


@pytest.fixture
def temp_json_file(sample_audit_logs):
    """Create a temporary JSON file with sample audit logs"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_audit_logs, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_json_dir(sample_audit_logs):
    """Create a temporary directory with multiple JSON files"""
    temp_dir = tempfile.mkdtemp()

    # Split logs into multiple files
    chunk_size = 2
    for i in range(0, len(sample_audit_logs), chunk_size):
        chunk = sample_audit_logs[i:i + chunk_size]
        file_path = os.path.join(temp_dir, f"audit-{i}.json")
        with open(file_path, 'w') as f:
            json.dump(chunk, f)

    yield temp_dir

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


# ============================================================================
# DuckDB Fixtures
# ============================================================================

@pytest.fixture
def duckdb_connection():
    """Create an in-memory DuckDB connection"""
    conn = duckdb.connect(":memory:")

    # Install extensions
    conn.execute("INSTALL json;")
    conn.execute("LOAD json;")

    yield conn

    conn.close()


@pytest.fixture
def duckdb_with_test_data(duckdb_connection, temp_json_file):
    """DuckDB connection with test data loaded"""
    conn = duckdb_connection

    # Create a view of the test data
    conn.execute(f"""
        CREATE VIEW test_logs AS
        SELECT * FROM read_json_auto('{temp_json_file}')
    """)

    yield conn


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_s3_bucket(monkeypatch):
    """Mock S3 bucket configuration"""
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("S3_PREFIX", "test-logs/")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")

    return {
        "bucket": "test-bucket",
        "prefix": "test-logs/",
        "region": "us-east-1"
    }


@pytest.fixture
def mock_env(monkeypatch):
    """Mock all environment variables"""
    env_vars = {
        "AWS_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "test-access-key",
        "AWS_SECRET_ACCESS_KEY": "test-secret-key",
        "S3_BUCKET": "test-eks-audit-bucket",
        "S3_PREFIX": "audit-logs/",
        "DUCKDB_MEMORY_LIMIT": "1GB",
        "DUCKDB_THREADS": "2",
        "HOST": "127.0.0.1",
        "PORT": "8000",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


# ============================================================================
# HTTP API Fixtures
# ============================================================================

@pytest.fixture
def http_client(mock_env, monkeypatch):
    """FastAPI test client for HTTP server"""
    # Prevent actual S3 connections during tests
    import sys
    import importlib

    # Mock the query engine initialization
    from unittest.mock import MagicMock, patch

    # We'll need to mock the DuckDB S3 initialization
    with patch('server.DuckDBQueryEngine._initialize_connection'):
        # Import after patching
        if 'http_server' in sys.modules:
            importlib.reload(sys.modules['http_server'])

        from http_server import app

        client = TestClient(app)
        yield client


# ============================================================================
# Time Fixtures
# ============================================================================

@pytest.fixture
def fixed_time():
    """Fixed time for consistent testing"""
    from freezegun import freeze_time

    fixed_datetime = datetime(2024, 1, 15, 12, 0, 0)
    with freeze_time(fixed_datetime):
        yield fixed_datetime


# ============================================================================
# Query Parser Fixtures
# ============================================================================

@pytest.fixture
def loki_parser():
    """LokiQueryParser instance"""
    from server import LokiQueryParser
    return LokiQueryParser()


@pytest.fixture
def ai_translator():
    """AIQueryTranslator instance"""
    from server import AIQueryTranslator
    return AIQueryTranslator()


# ============================================================================
# Parametrized Test Data
# ============================================================================

@pytest.fixture(params=[
    "create",
    "delete",
    "update",
    "patch",
    "get",
    "list",
    "watch"
])
def kubernetes_verb(request):
    """Parametrized Kubernetes verbs"""
    return request.param


@pytest.fixture(params=[
    200, 201, 204,  # Success codes
    400, 401, 403, 404, 500  # Error codes
])
def http_status_code(request):
    """Parametrized HTTP status codes"""
    return request.param


@pytest.fixture(params=[
    "production",
    "staging",
    "development",
    "kube-system",
    "default"
])
def kubernetes_namespace(request):
    """Parametrized Kubernetes namespaces"""
    return request.param
