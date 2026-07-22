# Testing Guide

This document describes the testing strategy and how to run tests for the EKS Audit Log Analyzer.

## Overview

The test suite includes:

- **Unit Tests**: Fast tests for individual components
- **Integration Tests**: Tests for complete workflows
- **Performance Tests**: Tests for performance characteristics
- **Mock Tests**: Tests using mocked dependencies
- **Real DuckDB Tests**: Tests with actual DuckDB queries

## Test Structure

```
tests/
├── __init__.py              # Package initialization
├── conftest.py              # Pytest fixtures and configuration
├── test_query_engine.py     # DuckDB query engine tests
├── test_parsers.py          # Loki and AI query parser tests
├── test_http_api.py         # HTTP API endpoint tests
├── test_mcp_tools.py        # FastMCP tool tests
└── test_integration.py      # Integration tests
```

## Installation

Install test dependencies:

```bash
pip install -r requirements.txt
```

This includes:
- pytest
- pytest-asyncio
- pytest-cov
- pytest-mock
- moto (for AWS mocking)
- freezegun (for time mocking)

## Running Tests

### Quick Start

Run all tests:
```bash
pytest
```

Or use the test runner script:
```bash
chmod +x run_tests.sh
./run_tests.sh all
```

### Test Categories

**Unit Tests Only (Fast)**
```bash
pytest -m unit
# or
./run_tests.sh unit
```

**Integration Tests Only**
```bash
pytest -m integration
# or
./run_tests.sh integration
```

**Specific Test Files**
```bash
pytest tests/test_query_engine.py
pytest tests/test_parsers.py
pytest tests/test_http_api.py
pytest tests/test_mcp_tools.py
```

**With Coverage Report**
```bash
pytest --cov=. --cov-report=html --cov-report=term
# or
./run_tests.sh coverage
```

View coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Test Markers

Tests are marked with pytest markers for selective execution:

```python
@pytest.mark.unit           # Unit tests (fast)
@pytest.mark.integration    # Integration tests
@pytest.mark.slow          # Slow running tests
@pytest.mark.requires_s3   # Requires S3 access
@pytest.mark.requires_aws  # Requires AWS credentials
```

Run specific markers:
```bash
pytest -m unit
pytest -m "not slow"
pytest -m "integration and not requires_s3"
```

## Test Components

### 1. Query Engine Tests (`test_query_engine.py`)

Tests for the DuckDB query engine:

- Connection initialization
- S3 configuration
- Query execution
- Filter application
- Time range queries
- Error handling
- Multi-file queries

Example:
```python
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
```

### 2. Parser Tests (`test_parsers.py`)

Tests for query parsers:

**LokiQueryParser Tests:**
- Time range parsing (s, m, h, d)
- LogQL filter parsing
- Include/exclude filters
- Complex query parsing

**AIQueryTranslator Tests:**
- Verb detection
- Namespace detection
- User detection
- Natural language understanding

Example:
```python
def test_parse_logql_multiple_filters(self, loki_parser):
    """Test parsing LogQL with multiple filters"""
    query = '{namespace="kube-system",verb="update"}'
    filters = loki_parser.parse_logql(query)

    assert filters == {
        'namespace': 'kube-system',
        'verb': 'update'
    }
```

### 3. HTTP API Tests (`test_http_api.py`)

Tests for FastAPI endpoints:

- Root and health endpoints
- `/query` endpoint
- `/loki/api/v1/query_range` endpoint
- `/ai/query` endpoint
- `/sql` endpoint
- `/stats` endpoint
- Error handling
- CORS configuration

Example:
```python
def test_query_with_verb_filter(self, sample_audit_logs):
    """Test query endpoint with verb filter"""
    from http_server import app

    mock_engine = Mock()
    mock_engine.query_eks_logs.return_value = sample_audit_logs

    with patch('http_server.query_engine', mock_engine):
        client = TestClient(app)
        response = client.get("/query?verb=create&limit=10")

        assert response.status_code == 200
```

### 4. MCP Tools Tests (`test_mcp_tools.py`)

Tests for FastMCP tools:

- `query_eks_audit_logs` tool
- `loki_style_query` tool
- `ai_agent_query` tool
- `get_eks_audit_schema` tool
- `execute_custom_sql` tool

Example:
```python
def test_basic_query(self, sample_audit_logs):
    """Test basic query without filters"""
    from server import query_eks_audit_logs

    mock_engine = Mock()
    mock_engine.query_eks_logs.return_value = sample_audit_logs

    with patch('server.query_engine', mock_engine):
        result = query_eks_audit_logs(limit=10)
        data = json.loads(result)

        assert data['status'] == 'success'
```

### 5. Integration Tests (`test_integration.py`)

End-to-end workflow tests:

- Complete query workflows
- Multi-file queries
- Filter combinations
- Error handling
- Performance tests
- Statistics calculation

Example:
```python
def test_complete_query_workflow(self, temp_json_file):
    """Test complete workflow from HTTP request to DuckDB query"""
    from http_server import app
    from server import DuckDBQueryEngine

    with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
        import http_server
        http_server.query_engine = DuckDBQueryEngine()

        client = TestClient(app)
        response = client.get("/query?limit=10")

        assert response.status_code == 200
```

## Fixtures

Common fixtures are defined in `conftest.py`:

### Data Fixtures
- `sample_audit_log`: Single audit log entry
- `sample_audit_logs`: Multiple audit log entries
- `temp_json_file`: Temporary JSON file with test data
- `temp_json_dir`: Temporary directory with multiple JSON files

### DuckDB Fixtures
- `duckdb_connection`: In-memory DuckDB connection
- `duckdb_with_test_data`: DuckDB with test data loaded

### Mock Fixtures
- `mock_s3_bucket`: Mocked S3 configuration
- `mock_env`: Mocked environment variables

### Time Fixtures
- `fixed_time`: Fixed time for consistent testing

### Parametrized Fixtures
- `kubernetes_verb`: Parametrized K8s verbs
- `http_status_code`: Parametrized HTTP codes
- `kubernetes_namespace`: Parametrized namespaces

## Mocking Strategy

Tests use mocking to avoid external dependencies:

```python
# Mock S3 paths
with patch.object(DuckDBQueryEngine, 'get_s3_path', return_value=temp_json_file):
    engine = DuckDBQueryEngine()
    results = engine.query_eks_logs()

# Mock query engine
mock_engine = Mock()
mock_engine.query_eks_logs.return_value = sample_data

with patch('server.query_engine', mock_engine):
    # Test code here
```

## Test Data

Test data is generated programmatically in fixtures:

```python
@pytest.fixture
def sample_audit_logs():
    """Generate sample audit logs"""
    base_time = datetime(2024, 1, 15, 10, 0, 0)

    return [
        {
            "timestamp": base_time.isoformat() + "Z",
            "verb": "create",
            "objectRef_namespace": "production",
            # ... more fields
        },
        # ... more logs
    ]
```

## Coverage Goals

Target coverage metrics:

- **Overall**: > 80%
- **Query Engine**: > 90%
- **Parsers**: > 85%
- **HTTP API**: > 80%
- **MCP Tools**: > 85%

Check coverage:
```bash
pytest --cov=. --cov-report=term-missing
```

## Continuous Integration

For CI/CD pipelines, use:

```bash
./run_tests.sh ci
```

This runs:
- All unit tests
- Integration tests (excluding S3-dependent tests)
- Coverage reporting
- XML report generation for CI tools

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Run tests
      run: |
        ./run_tests.sh ci

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Performance Testing

Run slow/performance tests:

```bash
pytest -m slow -v
```

Skip slow tests during development:

```bash
pytest -m "not slow"
```

## Debugging Tests

Run with verbose output:
```bash
pytest -vv
```

Run with print statements:
```bash
pytest -s
```

Run specific test:
```bash
pytest tests/test_query_engine.py::TestDuckDBQueryEngine::test_initialization -v
```

Drop into debugger on failure:
```bash
pytest --pdb
```

## Best Practices

1. **Keep tests fast**: Use mocks for external dependencies
2. **Test one thing**: Each test should verify one behavior
3. **Use descriptive names**: Test names should describe what they test
4. **Clean up resources**: Use fixtures for setup/teardown
5. **Parametrize similar tests**: Use `@pytest.mark.parametrize`
6. **Mock external calls**: Don't make real S3/AWS calls in tests
7. **Use appropriate markers**: Mark slow/integration tests properly

## Troubleshooting

### Import Errors

Ensure you're running tests from the project root:
```bash
cd samples/python/eks-audit-s3-analysis
pytest
```

### Missing Fixtures

Check that `conftest.py` is in the tests directory.

### DuckDB Extension Errors

Tests may try to install DuckDB extensions. Ensure write permissions:
```bash
mkdir -p ~/.duckdb/extensions
```

### Environment Variables

Tests mock environment variables. If tests fail due to env vars, check `mock_env` fixture.

## Writing New Tests

Template for new test:

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
class TestNewFeature:
    """Test new feature"""

    def test_basic_functionality(self, sample_data_fixture):
        """Test basic functionality of new feature"""
        # Arrange
        expected = "result"

        # Act
        result = new_feature(sample_data_fixture)

        # Assert
        assert result == expected

    def test_error_handling(self):
        """Test error handling"""
        with pytest.raises(ValueError):
            new_feature(invalid_input)
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Mocking in Python](https://docs.python.org/3/library/unittest.mock.html)
- [DuckDB Testing](https://duckdb.org/docs/dev/testing)

## Summary

```bash
# Quick commands
pytest                       # Run all tests
pytest -m unit              # Run unit tests only
pytest --cov=.              # Run with coverage
./run_tests.sh coverage     # Generate coverage report
./run_tests.sh ci           # Run CI test suite
```

For questions or issues with tests, check the test output and this guide first!
