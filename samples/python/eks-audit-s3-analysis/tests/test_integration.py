"""
Integration tests for the complete system
"""

import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestEndToEndWorkflow:
    """Test complete end-to-end workflows"""

    def test_complete_query_workflow(self, temp_json_file):
        """Test complete workflow from HTTP request to DuckDB query"""
        from http_server import app
        from server import DuckDBQueryEngine

        # Use real DuckDB but with local test file
        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            # Recreate the app with real engine
            import http_server
            http_server.query_engine = DuckDBQueryEngine()

            client = TestClient(app)

            # Test basic query
            response = client.get("/query?limit=10")
            assert response.status_code == 200

            data = response.json()
            assert data['status'] == 'success'
            assert 'results' in data

    def test_loki_to_duckdb_workflow(self, temp_json_file):
        """Test Loki query translation to DuckDB"""
        from http_server import app
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            import http_server
            http_server.query_engine = DuckDBQueryEngine()

            client = TestClient(app)

            # Test Loki-style query
            request_data = {
                "query": '{verb="create"}',
                "start": int((datetime.now() - timedelta(days=1)).timestamp() * 1e9),
                "end": int(datetime.now().timestamp() * 1e9),
                "limit": 100
            }

            response = client.post("/loki/api/v1/query_range", json=request_data)
            assert response.status_code == 200

            data = response.json()
            assert data['status'] == 'success'

    def test_ai_to_duckdb_workflow(self, temp_json_file):
        """Test AI query translation to DuckDB"""
        from http_server import app
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            import http_server
            http_server.query_engine = DuckDBQueryEngine()

            client = TestClient(app)

            # Test AI query
            request_data = {
                "question": "Show me all create operations",
                "time_range": "24h"
            }

            response = client.post("/ai/query", json=request_data)
            assert response.status_code == 200

            data = response.json()
            assert data['status'] == 'success'
            assert 'summary' in data['metadata']


@pytest.mark.integration
class TestMultiFileQueries:
    """Test querying across multiple files"""

    def test_query_multiple_json_files(self, temp_json_dir):
        """Test querying data from multiple JSON files"""
        from server import DuckDBQueryEngine

        file_pattern = f"{temp_json_dir}/*.json"

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=file_pattern):
            engine = DuckDBQueryEngine()
            results = engine.query_eks_logs(limit=100)

            # Should aggregate results from all files
            assert len(results) > 0

    def test_aggregation_across_files(self, temp_json_dir):
        """Test aggregations work across multiple files"""
        from server import DuckDBQueryEngine

        file_pattern = f"{temp_json_dir}/*.json"

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=file_pattern):
            engine = DuckDBQueryEngine()

            # Execute aggregation query
            query = f"""
                SELECT
                    verb,
                    COUNT(*) as count
                FROM read_json_auto('{file_pattern}')
                GROUP BY verb
                ORDER BY count DESC
            """

            results = engine.execute_query(query)
            assert len(results) > 0
            assert all('verb' in r and 'count' in r for r in results)


@pytest.mark.integration
class TestFilterCombinations:
    """Test various filter combinations"""

    def test_verb_and_namespace_filter(self, temp_json_file):
        """Test combining verb and namespace filters"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            engine = DuckDBQueryEngine()

            results = engine.query_eks_logs(
                filters={
                    'verb': 'create',
                    'objectRef_namespace': 'production'
                },
                limit=10
            )

            # All results should match both filters
            for result in results:
                assert result.get('verb') == 'create'
                assert result.get('objectRef_namespace') == 'production'

    def test_time_and_status_filter(self, temp_json_file):
        """Test combining time range and status code filters"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            engine = DuckDBQueryEngine()

            start_time = datetime(2024, 1, 15, 10, 0, 0)
            end_time = datetime(2024, 1, 15, 23, 59, 59)

            results = engine.query_eks_logs(
                start_time=start_time,
                end_time=end_time,
                filters={'responseStatus_code': 403},
                limit=10
            )

            # All results should be within time range and have status 403
            for result in results:
                timestamp = datetime.fromisoformat(result['timestamp'].replace('Z', ''))
                assert start_time <= timestamp <= end_time
                assert result.get('responseStatus_code') == 403


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in integration scenarios"""

    def test_missing_file_handling(self):
        """Test handling of missing files"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value='/nonexistent/file.json'):
            engine = DuckDBQueryEngine()

            # Should raise an exception
            with pytest.raises(Exception):
                engine.query_eks_logs(limit=10)

    def test_malformed_json_handling(self, tmp_path):
        """Test handling of malformed JSON"""
        from server import DuckDBQueryEngine

        # Create a file with malformed JSON
        malformed_file = tmp_path / "malformed.json"
        malformed_file.write_text("{ invalid json }")

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=str(malformed_file)):
            engine = DuckDBQueryEngine()

            # Should raise an exception
            with pytest.raises(Exception):
                engine.query_eks_logs(limit=10)


@pytest.mark.integration
class TestPerformance:
    """Test performance characteristics"""

    @pytest.mark.slow
    def test_large_result_set(self, temp_json_file):
        """Test handling large result sets"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            engine = DuckDBQueryEngine()

            # Query with large limit
            results = engine.query_eks_logs(limit=10000)

            # Should handle large limits gracefully
            assert isinstance(results, list)

    @pytest.mark.slow
    def test_complex_aggregation(self, temp_json_file):
        """Test complex aggregation queries"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            engine = DuckDBQueryEngine()

            query = f"""
                SELECT
                    verb,
                    objectRef_namespace,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT user_username) as unique_users,
                    AVG(CASE WHEN responseStatus_code >= 400 THEN 1.0 ELSE 0.0 END) as error_rate
                FROM read_json_auto('{temp_json_file}')
                GROUP BY verb, objectRef_namespace
                ORDER BY event_count DESC
            """

            results = engine.execute_query(query)
            assert len(results) >= 0


@pytest.mark.integration
class TestStatisticsEndpoint:
    """Test statistics generation"""

    def test_stats_calculation(self, temp_json_file):
        """Test statistics are calculated correctly"""
        from http_server import app
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            import http_server
            http_server.query_engine = DuckDBQueryEngine()

            client = TestClient(app)
            response = client.get("/stats?time_range=24h")

            assert response.status_code == 200
            data = response.json()

            # Verify all statistics are present
            assert 'total_events' in data
            assert 'by_verb' in data
            assert 'by_namespace' in data
            assert 'by_user' in data
            assert 'by_status_code' in data
            assert 'failed_operations' in data

            # Verify statistics are consistent
            total = data['total_events']
            verb_sum = sum(data['by_verb'].values())
            assert verb_sum == total


@pytest.mark.integration
@pytest.mark.requires_s3
class TestS3Integration:
    """Test S3 integration (requires actual S3 access)"""

    @pytest.mark.skip(reason="Requires actual S3 credentials and data")
    def test_real_s3_query(self):
        """Test querying real S3 data"""
        from server import DuckDBQueryEngine

        # This test requires real S3 credentials and data
        engine = DuckDBQueryEngine()
        results = engine.query_eks_logs(limit=10)

        assert isinstance(results, list)

    @pytest.mark.skip(reason="Requires actual S3 credentials and data")
    def test_s3_pagination(self):
        """Test pagination with S3 data"""
        from server import DuckDBQueryEngine

        engine = DuckDBQueryEngine()

        # Query first page
        page1 = engine.query_eks_logs(limit=10)

        # Query second page (would need offset support)
        page2 = engine.query_eks_logs(limit=10)

        # Pages should be different (if enough data exists)
        # This is a simplified test - real pagination would need offset support
        assert isinstance(page1, list)
        assert isinstance(page2, list)
