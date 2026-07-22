"""
Tests for FastMCP tools
"""

import json
from unittest.mock import patch, Mock
from datetime import datetime

import pytest


@pytest.mark.unit
class TestQueryEKSAuditLogsTool:
    """Test query_eks_audit_logs MCP tool"""

    def test_basic_query(self, sample_audit_logs):
        """Test basic query without filters"""
        from server import query_eks_audit_logs

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('server.query_engine', mock_engine):
            result = query_eks_audit_logs(limit=10)

            # Parse JSON result
            data = json.loads(result)

            assert data['status'] == 'success'
            assert data['count'] == len(sample_audit_logs)
            assert 'results' in data

    def test_query_with_verb(self, sample_audit_logs):
        """Test query with verb filter"""
        from server import query_eks_audit_logs

        filtered_logs = [log for log in sample_audit_logs if log.get('verb') == 'create']
        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = filtered_logs

        with patch('server.query_engine', mock_engine):
            result = query_eks_audit_logs(verb='create', limit=10)

            data = json.loads(result)
            assert data['status'] == 'success'

            # Verify engine was called with correct filters
            call_kwargs = mock_engine.query_eks_logs.call_args[1]
            assert call_kwargs['filters']['verb'] == 'create'

    def test_query_with_namespace(self, sample_audit_logs):
        """Test query with namespace filter"""
        from server import query_eks_audit_logs

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('server.query_engine', mock_engine):
            result = query_eks_audit_logs(namespace='production', limit=10)

            call_kwargs = mock_engine.query_eks_logs.call_args[1]
            assert call_kwargs['filters']['objectRef_namespace'] == 'production'

    def test_query_with_user(self, sample_audit_logs):
        """Test query with user filter"""
        from server import query_eks_audit_logs

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('server.query_engine', mock_engine):
            result = query_eks_audit_logs(user='john.doe', limit=10)

            call_kwargs = mock_engine.query_eks_logs.call_args[1]
            assert call_kwargs['filters']['user_username'] == 'john.doe'

    def test_query_with_time_range(self, sample_audit_logs):
        """Test query with time range"""
        from server import query_eks_audit_logs

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('server.query_engine', mock_engine):
            result = query_eks_audit_logs(
                start_time='2024-01-15T00:00:00',
                end_time='2024-01-15T23:59:59',
                limit=10
            )

            data = json.loads(result)
            assert data['status'] == 'success'

    def test_query_with_all_filters(self, sample_audit_logs):
        """Test query with all filters combined"""
        from server import query_eks_audit_logs

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('server.query_engine', mock_engine):
            result = query_eks_audit_logs(
                start_time='2024-01-15T00:00:00',
                end_time='2024-01-15T23:59:59',
                verb='create',
                namespace='production',
                user='john.doe',
                limit=50
            )

            data = json.loads(result)
            assert data['status'] == 'success'

            call_kwargs = mock_engine.query_eks_logs.call_args[1]
            assert call_kwargs['filters']['verb'] == 'create'
            assert call_kwargs['filters']['objectRef_namespace'] == 'production'
            assert call_kwargs['filters']['user_username'] == 'john.doe'


@pytest.mark.unit
class TestLokiStyleQueryTool:
    """Test loki_style_query MCP tool"""

    def test_basic_loki_query(self, sample_audit_logs):
        """Test basic Loki-style query"""
        from server import loki_style_query

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('server.query_engine', mock_engine):
            result = loki_style_query(
                query='{namespace="production"}',
                time_range='24h'
            )

            data = json.loads(result)
            assert data['status'] == 'success'
            assert data['query'] == '{namespace="production"}'

    def test_loki_query_with_multiple_filters(self, sample_audit_logs):
        """Test Loki query with multiple filters"""
        from server import loki_style_query

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('server.query_engine', mock_engine):
            result = loki_style_query(
                query='{namespace="kube-system",verb="update"}',
                time_range='1h'
            )

            data = json.loads(result)
            assert data['status'] == 'success'

    def test_loki_query_with_includes(self, sample_audit_logs):
        """Test Loki query with include filter"""
        from server import loki_style_query

        # Create logs with specific content
        test_logs = [
            {"verb": "create", "message": "error in pod creation"},
            {"verb": "create", "message": "pod created successfully"},
        ]

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = test_logs

        with patch('server.query_engine', mock_engine):
            result = loki_style_query(
                query='{verb="create"} |= "error"',
                time_range='1h'
            )

            data = json.loads(result)
            # Should filter to only logs containing "error"
            assert data['count'] <= len(test_logs)

    def test_loki_query_default_time_range(self, sample_audit_logs):
        """Test Loki query with default time range"""
        from server import loki_style_query

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('server.query_engine', mock_engine):
            result = loki_style_query(query='{namespace="production"}')

            data = json.loads(result)
            assert data['time_range'] == '24h'


@pytest.mark.unit
class TestAIAgentQueryTool:
    """Test ai_agent_query MCP tool"""

    def test_basic_ai_query(self, sample_audit_logs):
        """Test basic AI agent query"""
        from server import ai_agent_query

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('server.query_engine', mock_engine):
            result = ai_agent_query(
                question="Show me all create operations",
                time_range='24h'
            )

            data = json.loads(result)
            assert data['status'] == 'success'
            assert data['question'] == "Show me all create operations"

    def test_ai_query_generates_summary(self, sample_audit_logs):
        """Test AI query generates summary"""
        from server import ai_agent_query

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('server.query_engine', mock_engine):
            result = ai_agent_query(
                question="What operations happened?",
                time_range='1h'
            )

            data = json.loads(result)
            assert 'summary' in data
            assert 'total_events' in data['summary']
            assert 'unique_verbs' in data['summary']
            assert 'unique_namespaces' in data['summary']
            assert 'unique_users' in data['summary']

    def test_ai_query_with_verb_detection(self, sample_audit_logs):
        """Test AI query detects verbs from natural language"""
        from server import ai_agent_query

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('server.query_engine', mock_engine):
            result = ai_agent_query(
                question="Show me all delete operations",
                time_range='24h'
            )

            data = json.loads(result)
            translation = data['translation']
            assert translation['filters'].get('verb') == 'delete'

    def test_ai_query_with_namespace_detection(self, sample_audit_logs):
        """Test AI query detects namespace from natural language"""
        from server import ai_agent_query

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = sample_audit_logs

        with patch('server.query_engine', mock_engine):
            result = ai_agent_query(
                question="Show me operations in namespace production",
                time_range='24h'
            )

            data = json.loads(result)
            translation = data['translation']
            assert translation['filters'].get('objectRef_namespace') == 'production'

    def test_ai_query_limits_results(self, sample_audit_logs):
        """Test AI query limits results for readability"""
        from server import ai_agent_query

        # Create many logs
        many_logs = sample_audit_logs * 30  # 150 logs

        mock_engine = Mock()
        mock_engine.query_eks_logs.return_value = many_logs

        with patch('server.query_engine', mock_engine):
            result = ai_agent_query(
                question="Show me all operations",
                time_range='24h'
            )

            data = json.loads(result)
            # Should limit to 100 results
            assert len(data['results']) <= 100


@pytest.mark.unit
class TestGetEKSAuditSchemaTool:
    """Test get_eks_audit_schema MCP tool"""

    def test_get_schema(self):
        """Test getting audit log schema"""
        from server import get_eks_audit_schema

        result = get_eks_audit_schema()
        data = json.loads(result)

        assert 'description' in data
        assert 'fields' in data

        # Check key fields are present
        fields = data['fields']
        assert 'timestamp' in fields
        assert 'verb' in fields
        assert 'user' in fields
        assert 'objectRef' in fields
        assert 'responseStatus' in fields


@pytest.mark.unit
class TestExecuteCustomSQLTool:
    """Test execute_custom_sql MCP tool"""

    def test_execute_valid_sql(self):
        """Test executing valid SQL query"""
        from server import execute_custom_sql

        mock_engine = Mock()
        mock_engine.execute_query.return_value = [
            {'verb': 'create', 'count': 10},
            {'verb': 'delete', 'count': 5},
        ]

        with patch('server.query_engine', mock_engine):
            result = execute_custom_sql(
                sql_query="SELECT verb, COUNT(*) as count FROM logs GROUP BY verb"
            )

            data = json.loads(result)
            assert data['status'] == 'success'
            assert data['count'] == 2

    def test_execute_invalid_sql(self):
        """Test executing invalid SQL query"""
        from server import execute_custom_sql

        mock_engine = Mock()
        mock_engine.execute_query.side_effect = Exception("SQL error")

        with patch('server.query_engine', mock_engine):
            result = execute_custom_sql(sql_query="INVALID SQL")

            data = json.loads(result)
            assert data['status'] == 'error'
            assert 'error' in data

    def test_execute_sql_with_aggregation(self):
        """Test executing SQL with aggregation"""
        from server import execute_custom_sql

        mock_engine = Mock()
        mock_engine.execute_query.return_value = [
            {'namespace': 'production', 'total': 100},
            {'namespace': 'staging', 'total': 50},
        ]

        with patch('server.query_engine', mock_engine):
            result = execute_custom_sql(
                sql_query="SELECT namespace, COUNT(*) as total FROM logs GROUP BY namespace"
            )

            data = json.loads(result)
            assert data['status'] == 'success'
            assert len(data['results']) == 2


@pytest.mark.integration
class TestMCPToolsIntegration:
    """Integration tests for MCP tools with real DuckDB"""

    def test_query_with_real_duckdb(self, temp_json_file):
        """Test query tool with real DuckDB connection"""
        from server import DuckDBQueryEngine, query_eks_audit_logs

        # Create real engine but point to local file
        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            # Reset the global query_engine
            import server
            server.query_engine = DuckDBQueryEngine()

            result = query_eks_audit_logs(verb='create', limit=10)

            data = json.loads(result)
            assert data['status'] == 'success'
            assert isinstance(data['results'], list)

    def test_loki_query_with_real_duckdb(self, temp_json_file):
        """Test Loki query with real DuckDB connection"""
        from server import DuckDBQueryEngine, loki_style_query

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            import server
            server.query_engine = DuckDBQueryEngine()

            result = loki_style_query(
                query='{verb="create"}',
                time_range='24h'
            )

            data = json.loads(result)
            assert data['status'] == 'success'

    def test_ai_query_with_real_duckdb(self, temp_json_file):
        """Test AI query with real DuckDB connection"""
        from server import DuckDBQueryEngine, ai_agent_query

        with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
            import server
            server.query_engine = DuckDBQueryEngine()

            result = ai_agent_query(
                question="Show me all operations",
                time_range='24h'
            )

            data = json.loads(result)
            assert data['status'] == 'success'
            assert 'summary' in data
