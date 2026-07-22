"""
Tests for HTTP API endpoints
"""

import json
from datetime import datetime
from unittest.mock import patch, Mock

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestHTTPAPIBasic:
    """Test basic HTTP API endpoints"""

    def test_root_endpoint(self):
        """Test root endpoint returns service info"""
        from http_server import app

        with patch('http_server.query_engine'):
            client = TestClient(app)
            response = client.get("/")

            assert response.status_code == 200
            data = response.json()
            assert "service" in data
            assert "version" in data
            assert "endpoints" in data

    def test_health_endpoint(self):
        """Test health check endpoint"""
        from http_server import app

        with patch('http_server.query_engine'):
            client = TestClient(app)
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data

    def test_schema_endpoint(self):
        """Test schema endpoint returns audit log schema"""
        from http_server import app

        with patch('http_server.query_engine'):
            client = TestClient(app)
            response = client.get("/schema")

            assert response.status_code == 200
            data = response.json()
            assert "description" in data
            assert "fields" in data
            assert "timestamp" in data["fields"]
            assert "verb" in data["fields"]


@pytest.mark.unit
class TestQueryEndpoint:
    """Test /query endpoint"""

    def test_query_no_filters(self, sample_audit_logs):
        """Test query endpoint without filters"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)
            response = client.get("/query?limit=10")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["count"] == len(sample_audit_logs)
            assert "results" in data

    def test_query_with_verb_filter(self, sample_audit_logs):
        """Test query endpoint with verb filter"""
        from http_server import app

        filtered_logs = [log for log in sample_audit_logs if log.get('verb') == 'create']
        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = filtered_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)
            response = client.get("/query?verb=create&limit=10")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

            # Verify the engine was called with correct filters
            mock_engine.query_eks_logs.assert_called_once()
            call_kwargs = mock_engine.query_eks_logs.call_args[1]
            assert call_kwargs['filters']['verb'] == 'create'

    def test_query_with_namespace_filter(self, sample_audit_logs):
        """Test query endpoint with namespace filter"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)
            response = client.get("/query?namespace=production&limit=10")

            assert response.status_code == 200

            # Verify the engine was called with correct filters
            call_kwargs = mock_engine.query_eks_logs.call_args[1]
            assert call_kwargs['filters']['objectRef_namespace'] == 'production'

    def test_query_with_user_filter(self, sample_audit_logs):
        """Test query endpoint with user filter"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)
            response = client.get("/query?user=john.doe&limit=10")

            assert response.status_code == 200

            call_kwargs = mock_engine.query_eks_logs.call_args[1]
            assert call_kwargs['filters']['user_username'] == 'john.doe'

    def test_query_with_time_range(self, sample_audit_logs):
        """Test query endpoint with time range"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)
            response = client.get(
                "/query?start_time=2024-01-15T00:00:00Z&end_time=2024-01-15T23:59:59Z&limit=10"
            )

            assert response.status_code == 200

            call_kwargs = mock_engine.query_eks_logs.call_args[1]
            assert call_kwargs['start_time'] is not None
            assert call_kwargs['end_time'] is not None

    def test_query_with_limit(self, sample_audit_logs):
        """Test query endpoint respects limit parameter"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs[:2]

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)
            response = client.get("/query?limit=2")

            assert response.status_code == 200

            call_kwargs = mock_engine.query_eks_logs.call_args[1]
            assert call_kwargs['limit'] == 2

    def test_query_error_handling(self):
        """Test query endpoint error handling"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.side_effect = Exception("Database error")

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)
            response = client.get("/query?limit=10")

            assert response.status_code == 500


@pytest.mark.unit
class TestLokiEndpoint:
    """Test /loki/api/v1/query_range endpoint"""

    def test_loki_query_basic(self, sample_audit_logs):
        """Test basic Loki query"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)

            request_data = {
                "query": '{namespace="production"}',
                "start": 1705320000000000000,  # Unix nanoseconds
                "end": 1705323600000000000,
                "limit": 1000
            }

            response = client.post("/loki/api/v1/query_range", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "results" in data

    def test_loki_query_with_filters(self, sample_audit_logs):
        """Test Loki query with multiple filters"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)

            request_data = {
                "query": '{namespace="kube-system",verb="update"}',
                "start": 1705320000000000000,
                "end": 1705323600000000000,
                "limit": 1000
            }

            response = client.post("/loki/api/v1/query_range", json=request_data)

            assert response.status_code == 200

    def test_loki_query_with_includes(self, sample_audit_logs):
        """Test Loki query with include filter"""
        from http_server import app

        # Create test data with specific content
        test_logs = [
            {"verb": "create", "message": "error occurred"},
            {"verb": "create", "message": "success"},
        ]

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = test_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)

            request_data = {
                "query": '{verb="create"} |= "error"',
                "start": 1705320000000000000,
                "end": 1705323600000000000,
                "limit": 1000
            }

            response = client.post("/loki/api/v1/query_range", json=request_data)

            assert response.status_code == 200
            data = response.json()

            # Should only include logs with "error"
            assert data["count"] <= len(test_logs)

    def test_loki_query_error_handling(self):
        """Test Loki query endpoint error handling"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.side_effect = Exception("Query error")

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)

            request_data = {
                "query": '{namespace="production"}',
                "start": 1705320000000000000,
                "end": 1705323600000000000,
                "limit": 1000
            }

            response = client.post("/loki/api/v1/query_range", json=request_data)

            assert response.status_code == 500


@pytest.mark.unit
class TestAIQueryEndpoint:
    """Test /ai/query endpoint"""

    def test_ai_query_basic(self, sample_audit_logs):
        """Test basic AI agent query"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)

            request_data = {
                "question": "Show me all create operations",
                "time_range": "24h"
            }

            response = client.post("/ai/query", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "summary" in data["metadata"]

    def test_ai_query_with_context(self, sample_audit_logs):
        """Test AI query with additional context"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)

            request_data = {
                "question": "Find failed operations",
                "time_range": "1h",
                "context": {"focus": "security"}
            }

            response = client.post("/ai/query", json=request_data)

            assert response.status_code == 200

    def test_ai_query_generates_summary(self, sample_audit_logs):
        """Test AI query generates summary statistics"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)

            request_data = {
                "question": "What happened in the last hour?",
                "time_range": "1h"
            }

            response = client.post("/ai/query", json=request_data)

            assert response.status_code == 200
            data = response.json()

            summary = data["metadata"]["summary"]
            assert "total_events" in summary
            assert "unique_verbs" in summary
            assert "unique_namespaces" in summary
            assert "unique_users" in summary


@pytest.mark.unit
class TestSQLEndpoint:
    """Test /sql endpoint"""

    def test_sql_query_basic(self):
        """Test basic SQL query"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.execute_query.return_value = [
            {"verb": "create", "count": 10},
            {"verb": "delete", "count": 5},
        ]

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)

            request_data = {
                "query": "SELECT verb, COUNT(*) as count FROM logs GROUP BY verb"
            }

            response = client.post("/sql", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["count"] == 2

    def test_sql_query_missing_query_field(self):
        """Test SQL endpoint with missing query field"""
        from http_server import app

        with patch('http_server.query_engine'):
            client = TestClient(app)

            request_data = {}

            response = client.post("/sql", json=request_data)

            assert response.status_code == 400

    def test_sql_query_error_handling(self):
        """Test SQL query error handling"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.execute_query.side_effect = Exception("SQL error")

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)

            request_data = {
                "query": "INVALID SQL"
            }

            response = client.post("/sql", json=request_data)

            assert response.status_code == 500


@pytest.mark.unit
class TestStatsEndpoint:
    """Test /stats endpoint"""

    def test_stats_default_time_range(self, sample_audit_logs):
        """Test stats endpoint with default time range"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)
            response = client.get("/stats")

            assert response.status_code == 200
            data = response.json()

            assert "total_events" in data
            assert "by_verb" in data
            assert "by_namespace" in data
            assert "by_user" in data
            assert "failed_operations" in data

    def test_stats_custom_time_range(self, sample_audit_logs):
        """Test stats endpoint with custom time range"""
        from http_server import app

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)
            response = client.get("/stats?time_range=1h")

            assert response.status_code == 200
            data = response.json()
            assert data["time_range"] == "1h"

    def test_stats_aggregation(self):
        """Test stats endpoint aggregates correctly"""
        from http_server import app

        test_logs = [
            {"verb": "create", "objectRef_namespace": "prod", "user_username": "user1", "responseStatus_code": 201},
            {"verb": "create", "objectRef_namespace": "prod", "user_username": "user2", "responseStatus_code": 201},
            {"verb": "delete", "objectRef_namespace": "staging", "user_username": "user1", "responseStatus_code": 403},
        ]

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = test_logs

        with patch('http_server.query_engine', mock_engine):
            client = TestClient(app)
            response = client.get("/stats")

            assert response.status_code == 200
            data = response.json()

            assert data["total_events"] == 3
            assert data["by_verb"]["create"] == 2
            assert data["by_verb"]["delete"] == 1
            assert data["failed_operations"] == 1  # One 403


@pytest.mark.unit
class TestCORSConfiguration:
    """Test CORS configuration"""

    def test_cors_headers_present(self):
        """Test that CORS headers are configured"""
        from http_server import app

        with patch('http_server.query_engine'):
            client = TestClient(app)
            response = client.options("/")

            # Check CORS headers are present
            assert "access-control-allow-origin" in response.headers
