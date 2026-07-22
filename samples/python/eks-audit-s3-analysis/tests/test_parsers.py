"""
Unit tests for query parsers (Loki and AI)
"""

import pytest
from datetime import timedelta


@pytest.mark.unit
class TestLokiQueryParser:
    """Test LokiQueryParser class"""

    def test_parse_time_range_seconds(self, loki_parser):
        """Test parsing time range in seconds"""
        delta = loki_parser.parse_time_range("30s")
        assert delta == timedelta(seconds=30)

    def test_parse_time_range_minutes(self, loki_parser):
        """Test parsing time range in minutes"""
        delta = loki_parser.parse_time_range("15m")
        assert delta == timedelta(minutes=15)

    def test_parse_time_range_hours(self, loki_parser):
        """Test parsing time range in hours"""
        delta = loki_parser.parse_time_range("24h")
        assert delta == timedelta(hours=24)

    def test_parse_time_range_days(self, loki_parser):
        """Test parsing time range in days"""
        delta = loki_parser.parse_time_range("7d")
        assert delta == timedelta(days=7)

    def test_parse_time_range_invalid(self, loki_parser):
        """Test parsing invalid time range defaults to 24h"""
        delta = loki_parser.parse_time_range("invalid")
        assert delta == timedelta(hours=24)

    def test_parse_logql_simple_filter(self, loki_parser):
        """Test parsing simple LogQL filter"""
        query = '{namespace="production"}'
        filters = loki_parser.parse_logql(query)

        assert filters == {'namespace': 'production'}

    def test_parse_logql_multiple_filters(self, loki_parser):
        """Test parsing LogQL with multiple filters"""
        query = '{namespace="kube-system",verb="update"}'
        filters = loki_parser.parse_logql(query)

        assert filters == {
            'namespace': 'kube-system',
            'verb': 'update'
        }

    def test_parse_logql_with_includes(self, loki_parser):
        """Test parsing LogQL with include filter"""
        query = '{namespace="production"} |= "error"'
        filters = loki_parser.parse_logql(query)

        assert filters['namespace'] == 'production'
        assert filters['_includes'] == ['error']

    def test_parse_logql_with_excludes(self, loki_parser):
        """Test parsing LogQL with exclude filter"""
        query = '{verb="create"} != "success"'
        filters = loki_parser.parse_logql(query)

        assert filters['verb'] == 'create'
        assert filters['_excludes'] == ['success']

    def test_parse_logql_with_multiple_includes(self, loki_parser):
        """Test parsing LogQL with multiple includes"""
        query = '{namespace="production"} |= "error" |= "failed"'
        filters = loki_parser.parse_logql(query)

        assert filters['_includes'] == ['error', 'failed']

    def test_parse_logql_complex(self, loki_parser):
        """Test parsing complex LogQL query"""
        query = '{namespace="kube-system",verb="update",user="admin"} |= "pod" != "success"'
        filters = loki_parser.parse_logql(query)

        assert filters['namespace'] == 'kube-system'
        assert filters['verb'] == 'update'
        assert filters['user'] == 'admin'
        assert filters['_includes'] == ['pod']
        assert filters['_excludes'] == ['success']

    def test_parse_logql_empty_query(self, loki_parser):
        """Test parsing empty LogQL query"""
        query = ''
        filters = loki_parser.parse_logql(query)

        assert filters == {}

    def test_parse_logql_no_filters(self, loki_parser):
        """Test parsing LogQL with no filter section"""
        query = '|= "error"'
        filters = loki_parser.parse_logql(query)

        assert filters == {'_includes': ['error']}

    @pytest.mark.parametrize("time_str,expected", [
        ("1s", timedelta(seconds=1)),
        ("60s", timedelta(seconds=60)),
        ("5m", timedelta(minutes=5)),
        ("1h", timedelta(hours=1)),
        ("3d", timedelta(days=3)),
    ])
    def test_parse_time_range_parametrized(self, loki_parser, time_str, expected):
        """Test parsing various time range formats"""
        delta = loki_parser.parse_time_range(time_str)
        assert delta == expected


@pytest.mark.unit
class TestAIQueryTranslator:
    """Test AIQueryTranslator class"""

    def test_translate_failed_operations(self, ai_translator):
        """Test translating query about failed operations"""
        question = "show me all failed pod creations"
        translation = ai_translator.translate_question(question)

        assert 'filters' in translation
        # Should detect "failed" and "create"

    def test_translate_create_verb(self, ai_translator):
        """Test translating query with create verb"""
        question = "show me all create operations"
        translation = ai_translator.translate_question(question)

        assert translation['filters'].get('verb') == 'create'

    def test_translate_delete_verb(self, ai_translator):
        """Test translating query with delete verb"""
        question = "find all delete operations"
        translation = ai_translator.translate_question(question)

        assert translation['filters'].get('verb') == 'delete'

    def test_translate_update_verb(self, ai_translator):
        """Test translating query with update verb"""
        question = "show me update operations"
        translation = ai_translator.translate_question(question)

        assert translation['filters'].get('verb') == 'update'

    def test_translate_get_verb(self, ai_translator):
        """Test translating query with get verb"""
        question = "show me all get requests"
        translation = ai_translator.translate_question(question)

        assert translation['filters'].get('verb') == 'get'

    def test_translate_with_namespace(self, ai_translator):
        """Test translating query with namespace"""
        question = "show me operations in namespace production"
        translation = ai_translator.translate_question(question)

        assert translation['filters'].get('objectRef_namespace') == 'production'

    def test_translate_with_user(self, ai_translator):
        """Test translating query with user"""
        question = "what did user john.doe do"
        translation = ai_translator.translate_question(question)

        assert translation['filters'].get('user_username') == 'john.doe'

    def test_translate_complex_question(self, ai_translator):
        """Test translating complex natural language question"""
        question = "show me all delete operations by user admin in namespace kube-system"
        translation = ai_translator.translate_question(question)

        filters = translation['filters']
        assert filters.get('verb') == 'delete'
        assert filters.get('user_username') == 'admin'
        assert filters.get('objectRef_namespace') == 'kube-system'

    def test_translate_with_custom_time_range(self, ai_translator):
        """Test translating with custom time range"""
        question = "show me recent operations"
        translation = ai_translator.translate_question(question, time_range="1h")

        assert translation['time_range'] == '1h'

    def test_translate_case_insensitive(self, ai_translator):
        """Test that translation is case insensitive"""
        question1 = "SHOW ME CREATE OPERATIONS"
        question2 = "show me create operations"

        translation1 = ai_translator.translate_question(question1)
        translation2 = ai_translator.translate_question(question2)

        assert translation1['filters'] == translation2['filters']

    def test_translate_empty_question(self, ai_translator):
        """Test translating empty question"""
        question = ""
        translation = ai_translator.translate_question(question)

        assert 'filters' in translation
        assert 'time_range' in translation

    @pytest.mark.parametrize("question,expected_verb", [
        ("create a pod", "create"),
        ("delete resources", "delete"),
        ("update configuration", "update"),
        ("get pods", "get"),
        ("read logs", "get"),
    ])
    def test_translate_verb_detection(self, ai_translator, question, expected_verb):
        """Test verb detection from various phrasings"""
        translation = ai_translator.translate_question(question)

        assert translation['filters'].get('verb') == expected_verb

    @pytest.mark.parametrize("namespace", ["production", "staging", "kube-system", "default"])
    def test_translate_namespace_detection(self, ai_translator, namespace):
        """Test namespace detection"""
        question = f"show me operations in namespace {namespace}"
        translation = ai_translator.translate_question(question)

        assert translation['filters'].get('objectRef_namespace') == namespace

    def test_translate_error_keyword(self, ai_translator):
        """Test detection of error keyword"""
        question = "show me all error events"
        translation = ai_translator.translate_question(question)

        # Should have some filter related to errors
        assert 'filters' in translation

    def test_translate_failed_keyword(self, ai_translator):
        """Test detection of failed keyword"""
        question = "find failed operations"
        translation = ai_translator.translate_question(question)

        # Should detect failed operations (403 status)
        filters = translation['filters']
        assert 'verb' in filters or 'responseStatus_code' in filters
