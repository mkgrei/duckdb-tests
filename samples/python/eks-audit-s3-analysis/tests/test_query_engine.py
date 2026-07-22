"""
Unit tests for DuckDBQueryEngine
"""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import pytest
import duckdb


@pytest.mark.unit
class TestDuckDBQueryEngine:
    """Test DuckDBQueryEngine class"""

    @patch('server.duckdb.connect')
    def test_initialization(self, mock_connect):
        """Test query engine initialization"""
        from server import DuckDBQueryEngine

        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        engine = DuckDBQueryEngine()

        # Verify connection was created
        mock_connect.assert_called_once_with(":memory:")

        # Verify extensions were installed and loaded
        execute_calls = [call[0][0] for call in mock_conn.execute.call_args_list]

        assert "INSTALL httpfs;" in execute_calls
        assert "LOAD httpfs;" in execute_calls
        assert "INSTALL json;" in execute_calls
        assert "LOAD json;" in execute_calls

    @patch('server.duckdb.connect')
    def test_s3_configuration(self, mock_connect, mock_s3_bucket):
        """Test S3 credentials configuration"""
        from server import DuckDBQueryEngine

        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        engine = DuckDBQueryEngine()

        execute_calls = [call[0][0] for call in mock_conn.execute.call_args_list]

        # Check that S3 settings were configured
        assert any("SET s3_region=" in call for call in execute_calls)
        assert any("SET s3_access_key_id=" in call for call in execute_calls)
        assert any("SET s3_secret_access_key=" in call for call in execute_calls)

    def test_get_s3_path_default(self, mock_s3_bucket):
        """Test S3 path generation with default prefix"""
        from server import DuckDBQueryEngine

        with patch('server.duckdb.connect'):
            engine = DuckDBQueryEngine()
            path = engine.get_s3_path()

            assert path == "s3://test-bucket/test-logs/*.json"

    def test_get_s3_path_custom_prefix(self, mock_s3_bucket):
        """Test S3 path generation with custom prefix"""
        from server import DuckDBQueryEngine

        with patch('server.duckdb.connect'):
            engine = DuckDBQueryEngine()
            path = engine.get_s3_path("2024/01/15/")

            assert path == "s3://test-bucket/test-logs/2024/01/15/*.json"

    def test_execute_query_basic(self, duckdb_connection):
        """Test basic query execution"""
        from server import DuckDBQueryEngine

        with patch('server.duckdb.connect', return_value=duckdb_connection):
            engine = DuckDBQueryEngine()

            # Create test data
            duckdb_connection.execute("""
                CREATE TABLE test_table AS
                SELECT 'value1' as col1, 123 as col2
                UNION ALL
                SELECT 'value2' as col1, 456 as col2
            """)

            # Execute query
            results = engine.execute_query("SELECT * FROM test_table ORDER BY col2")

            # Verify results
            assert len(results) == 2
            assert results[0] == {'col1': 'value1', 'col2': 123}
            assert results[1] == {'col1': 'value2', 'col2': 456}

    def test_execute_query_with_filters(self, duckdb_connection):
        """Test query execution with WHERE clause"""
        from server import DuckDBQueryEngine

        with patch('server.duckdb.connect', return_value=duckdb_connection):
            engine = DuckDBQueryEngine()

            # Create test data
            duckdb_connection.execute("""
                CREATE TABLE logs AS
                SELECT 'create' as verb, 'production' as namespace, 201 as code
                UNION ALL
                SELECT 'delete' as verb, 'staging' as namespace, 200 as code
                UNION ALL
                SELECT 'create' as verb, 'production' as namespace, 403 as code
            """)

            # Execute filtered query
            results = engine.execute_query("""
                SELECT * FROM logs
                WHERE verb = 'create' AND namespace = 'production'
                ORDER BY code
            """)

            # Verify results
            assert len(results) == 2
            assert all(r['verb'] == 'create' for r in results)
            assert all(r['namespace'] == 'production' for r in results)

    def test_query_eks_logs_no_filters(self, temp_json_file):
        """Test querying logs without filters"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            engine = DuckDBQueryEngine()
            results = engine.query_eks_logs(limit=10)

            assert len(results) > 0
            assert isinstance(results, list)
            assert all(isinstance(r, dict) for r in results)

    def test_query_eks_logs_with_verb_filter(self, temp_json_file):
        """Test querying logs with verb filter"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            engine = DuckDBQueryEngine()
            results = engine.query_eks_logs(
                filters={'verb': 'create'},
                limit=10
            )

            assert all(r.get('verb') == 'create' for r in results)

    def test_query_eks_logs_with_namespace_filter(self, temp_json_file):
        """Test querying logs with namespace filter"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            engine = DuckDBQueryEngine()
            results = engine.query_eks_logs(
                filters={'objectRef_namespace': 'production'},
                limit=10
            )

            assert all(r.get('objectRef_namespace') == 'production' for r in results)

    def test_query_eks_logs_with_time_range(self, temp_json_file):
        """Test querying logs with time range"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            engine = DuckDBQueryEngine()

            start_time = datetime(2024, 1, 15, 10, 0, 0)
            end_time = datetime(2024, 1, 15, 10, 15, 0)

            results = engine.query_eks_logs(
                start_time=start_time,
                end_time=end_time,
                limit=10
            )

            # Verify all results are within time range
            for result in results:
                timestamp = datetime.fromisoformat(result['timestamp'].replace('Z', ''))
                assert start_time <= timestamp <= end_time

    def test_query_eks_logs_with_multiple_filters(self, temp_json_file):
        """Test querying logs with multiple filters"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            engine = DuckDBQueryEngine()

            results = engine.query_eks_logs(
                filters={
                    'verb': 'create',
                    'responseStatus_code': 403
                },
                limit=10
            )

            # Verify all filters are applied
            for result in results:
                assert result.get('verb') == 'create'
                assert result.get('responseStatus_code') == 403

    def test_query_eks_logs_with_limit(self, temp_json_file):
        """Test querying logs with result limit"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            engine = DuckDBQueryEngine()

            results = engine.query_eks_logs(limit=2)

            assert len(results) <= 2

    def test_query_eks_logs_empty_result(self, temp_json_file):
        """Test querying logs with filter that matches nothing"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            engine = DuckDBQueryEngine()

            results = engine.query_eks_logs(
                filters={'verb': 'nonexistent'},
                limit=10
            )

            assert len(results) == 0
            assert isinstance(results, list)

    def test_query_multiple_files(self, temp_json_dir):
        """Test querying multiple JSON files"""
        from server import DuckDBQueryEngine

        file_pattern = f"{temp_json_dir}/*.json"

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=file_pattern):
            engine = DuckDBQueryEngine()
            results = engine.query_eks_logs(limit=100)

            # Should get results from all files
            assert len(results) > 0

    def test_execute_query_error_handling(self):
        """Test query execution error handling"""
        from server import DuckDBQueryEngine

        with patch('server.duckdb.connect'):
            engine = DuckDBQueryEngine()

            # Invalid SQL should raise an exception
            with pytest.raises(Exception):
                engine.execute_query("INVALID SQL QUERY")

    @pytest.mark.parametrize("verb", ["create", "delete", "update", "get", "list"])
    def test_query_different_verbs(self, temp_json_file, verb):
        """Test querying with different Kubernetes verbs"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            engine = DuckDBQueryEngine()

            # This should not raise errors even if no results
            results = engine.query_eks_logs(
                filters={'verb': verb},
                limit=10
            )

            # All results should match the verb if any exist
            for result in results:
                assert result.get('verb') == verb

    def test_query_with_status_code_filter(self, temp_json_file):
        """Test querying with HTTP status code filter"""
        from server import DuckDBQueryEngine

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            engine = DuckDBQueryEngine()

            # Query for failed operations (status >= 400)
            results = engine.query_eks_logs(limit=100)

            # Filter in Python to verify
            failed_ops = [r for r in results if r.get('responseStatus_code', 0) >= 400]

            # Now query with filter
            filtered_results = engine.query_eks_logs(
                filters={'responseStatus_code': 403},
                limit=100
            )

            # All should have status 403
            for result in filtered_results:
                assert result.get('responseStatus_code') == 403
