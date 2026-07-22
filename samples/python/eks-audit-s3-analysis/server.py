#!/usr/bin/env python3
"""
FastMCP Server for EKS Audit Log Analysis using DuckDB and S3

This server provides:
1. Direct S3 querying with DuckDB
2. Grafana Loki-style query interface
3. AI agent dynamic query support
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import duckdb
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX", "eks-audit-logs/")
DUCKDB_MEMORY_LIMIT = os.getenv("DUCKDB_MEMORY_LIMIT", "4GB")
DUCKDB_THREADS = int(os.getenv("DUCKDB_THREADS", "4"))


class DuckDBQueryEngine:
    """DuckDB query engine for S3 data"""

    def __init__(self):
        self.conn = None
        self._initialize_connection()

    def _initialize_connection(self):
        """Initialize DuckDB connection with S3 support"""
        self.conn = duckdb.connect(":memory:")

        # Install and load extensions
        self.conn.execute("INSTALL httpfs;")
        self.conn.execute("LOAD httpfs;")
        self.conn.execute("INSTALL json;")
        self.conn.execute("LOAD json;")

        # Configure DuckDB
        self.conn.execute(f"SET memory_limit='{DUCKDB_MEMORY_LIMIT}';")
        self.conn.execute(f"SET threads={DUCKDB_THREADS};")

        # Configure S3 credentials
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            self.conn.execute(f"SET s3_region='{AWS_REGION}';")
            self.conn.execute(f"SET s3_access_key_id='{AWS_ACCESS_KEY_ID}';")
            self.conn.execute(f"SET s3_secret_access_key='{AWS_SECRET_ACCESS_KEY}';")

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a DuckDB query and return results as list of dicts"""
        result = self.conn.execute(query).fetchall()
        columns = [desc[0] for desc in self.conn.description]
        return [dict(zip(columns, row)) for row in result]

    def get_s3_path(self, prefix: str = "") -> str:
        """Get full S3 path for queries"""
        full_prefix = f"{S3_PREFIX}{prefix}" if prefix else S3_PREFIX
        return f"s3://{S3_BUCKET}/{full_prefix}*.json"

    def query_eks_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query EKS audit logs with filters"""

        s3_path = self.get_s3_path()

        # Build WHERE clause
        where_clauses = []

        if start_time:
            where_clauses.append(f"timestamp >= '{start_time.isoformat()}'")

        if end_time:
            where_clauses.append(f"timestamp <= '{end_time.isoformat()}'")

        if filters:
            for key, value in filters.items():
                if isinstance(value, str):
                    where_clauses.append(f"{key} = '{value}'")
                else:
                    where_clauses.append(f"{key} = {value}")

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
        SELECT *
        FROM read_json_auto('{s3_path}')
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT {limit}
        """

        return self.execute_query(query)


class LokiQueryRequest(BaseModel):
    """Grafana Loki-style query request"""
    query: str = Field(..., description="LogQL-style query string")
    start: int = Field(..., description="Start timestamp (Unix nanoseconds)")
    end: int = Field(..., description="End timestamp (Unix nanoseconds)")
    limit: int = Field(default=1000, description="Maximum number of logs to return")
    direction: str = Field(default="backward", description="Query direction: forward or backward")


class AIAgentQueryRequest(BaseModel):
    """AI agent natural language query request"""
    question: str = Field(..., description="Natural language question about the logs")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context for the query")
    time_range: Optional[str] = Field(default="24h", description="Time range (e.g., '1h', '24h', '7d')")


class LokiQueryParser:
    """Parse Loki-style queries to DuckDB SQL"""

    @staticmethod
    def parse_time_range(time_str: str) -> timedelta:
        """Parse time range string (e.g., '1h', '24h', '7d')"""
        match = re.match(r'(\d+)([smhd])', time_str)
        if not match:
            return timedelta(hours=24)

        value, unit = int(match.group(1)), match.group(2)

        unit_map = {
            's': timedelta(seconds=value),
            'm': timedelta(minutes=value),
            'h': timedelta(hours=value),
            'd': timedelta(days=value)
        }

        return unit_map.get(unit, timedelta(hours=24))

    @staticmethod
    def parse_logql(query: str) -> Dict[str, Any]:
        """
        Parse LogQL-style query to filters
        Example: {namespace="kube-system",verb="get"}
        """
        filters = {}

        # Extract filters from curly braces
        match = re.search(r'\{([^}]+)\}', query)
        if match:
            filter_str = match.group(1)

            # Parse key="value" pairs
            for pair in re.findall(r'(\w+)="([^"]+)"', filter_str):
                key, value = pair
                filters[key] = value

        # Extract additional filters
        # Support patterns like |= "error", != "success"
        includes = re.findall(r'\|=\s*"([^"]+)"', query)
        excludes = re.findall(r'!=\s*"([^"]+)"', query)

        if includes:
            filters['_includes'] = includes
        if excludes:
            filters['_excludes'] = excludes

        return filters


class AIQueryTranslator:
    """Translate natural language queries to DuckDB SQL"""

    @staticmethod
    def translate_question(question: str, time_range: str = "24h") -> Dict[str, Any]:
        """
        Translate natural language question to query parameters
        This is a simple rule-based translator. In production, use an LLM.
        """
        question_lower = question.lower()
        filters = {}

        # Detect common patterns
        if "failed" in question_lower or "error" in question_lower:
            filters['verb'] = 'create'
            filters['responseStatus_code'] = 403

        if "create" in question_lower:
            filters['verb'] = 'create'
        elif "delete" in question_lower:
            filters['verb'] = 'delete'
        elif "update" in question_lower:
            filters['verb'] = 'update'
        elif "get" in question_lower or "read" in question_lower:
            filters['verb'] = 'get'

        # Extract namespace
        namespace_match = re.search(r'namespace\s+(\S+)', question_lower)
        if namespace_match:
            filters['objectRef_namespace'] = namespace_match.group(1)

        # Extract user
        user_match = re.search(r'user\s+(\S+)', question_lower)
        if user_match:
            filters['user_username'] = user_match.group(1)

        return {
            'filters': filters,
            'time_range': time_range
        }


# Initialize FastMCP server
mcp = FastMCP("EKS Audit Log Analyzer")

# Initialize query engine
query_engine = DuckDBQueryEngine()


@mcp.tool()
def query_eks_audit_logs(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    verb: Optional[str] = None,
    namespace: Optional[str] = None,
    user: Optional[str] = None,
    limit: int = 100
) -> str:
    """
    Query EKS audit logs from S3 using DuckDB

    Args:
        start_time: Start time in ISO format (optional)
        end_time: End time in ISO format (optional)
        verb: Kubernetes verb (get, list, create, update, delete, etc.)
        namespace: Kubernetes namespace
        user: Username who performed the action
        limit: Maximum number of results (default: 100)

    Returns:
        JSON string with query results
    """
    filters = {}

    if verb:
        filters['verb'] = verb
    if namespace:
        filters['objectRef_namespace'] = namespace
    if user:
        filters['user_username'] = user

    start_dt = datetime.fromisoformat(start_time) if start_time else None
    end_dt = datetime.fromisoformat(end_time) if end_time else None

    results = query_engine.query_eks_logs(
        start_time=start_dt,
        end_time=end_dt,
        filters=filters,
        limit=limit
    )

    return json.dumps({
        'status': 'success',
        'count': len(results),
        'results': results
    }, indent=2)


@mcp.tool()
def loki_style_query(
    query: str,
    time_range: str = "24h",
    limit: int = 1000
) -> str:
    """
    Query EKS audit logs using Grafana Loki-style syntax

    Args:
        query: LogQL-style query (e.g., '{namespace="kube-system",verb="create"}')
        time_range: Time range (e.g., '1h', '24h', '7d')
        limit: Maximum number of results

    Returns:
        JSON string with query results
    """
    # Parse LogQL query
    filters = LokiQueryParser.parse_logql(query)

    # Calculate time range
    delta = LokiQueryParser.parse_time_range(time_range)
    end_time = datetime.utcnow()
    start_time = end_time - delta

    # Remove special filters
    includes = filters.pop('_includes', [])
    excludes = filters.pop('_excludes', [])

    # Execute query
    results = query_engine.query_eks_logs(
        start_time=start_time,
        end_time=end_time,
        filters=filters,
        limit=limit
    )

    # Apply includes/excludes filters (post-processing)
    if includes or excludes:
        filtered_results = []
        for result in results:
            result_str = json.dumps(result).lower()

            # Check includes
            if includes:
                if not any(term.lower() in result_str for term in includes):
                    continue

            # Check excludes
            if excludes:
                if any(term.lower() in result_str for term in excludes):
                    continue

            filtered_results.append(result)

        results = filtered_results

    return json.dumps({
        'status': 'success',
        'query': query,
        'time_range': time_range,
        'count': len(results),
        'results': results
    }, indent=2)


@mcp.tool()
def ai_agent_query(
    question: str,
    time_range: str = "24h"
) -> str:
    """
    Query EKS audit logs using natural language (AI agent interface)

    Args:
        question: Natural language question about the logs
        time_range: Time range to search (e.g., '1h', '24h', '7d')

    Returns:
        JSON string with query results and interpretation

    Examples:
        - "Show me all failed pod creations in the last hour"
        - "What did user john do in namespace production?"
        - "Find all delete operations in the last 24 hours"
    """
    # Translate question to query parameters
    translation = AIQueryTranslator.translate_question(question, time_range)

    # Calculate time range
    delta = LokiQueryParser.parse_time_range(translation['time_range'])
    end_time = datetime.utcnow()
    start_time = end_time - delta

    # Execute query
    results = query_engine.query_eks_logs(
        start_time=start_time,
        end_time=end_time,
        filters=translation['filters'],
        limit=1000
    )

    # Generate summary
    summary = {
        'total_events': len(results),
        'unique_verbs': list(set(r.get('verb', 'unknown') for r in results)),
        'unique_namespaces': list(set(r.get('objectRef_namespace', 'unknown') for r in results)),
        'unique_users': list(set(r.get('user_username', 'unknown') for r in results))
    }

    return json.dumps({
        'status': 'success',
        'question': question,
        'time_range': time_range,
        'translation': translation,
        'summary': summary,
        'count': len(results),
        'results': results[:100]  # Limit to first 100 for readability
    }, indent=2)


@mcp.tool()
def get_eks_audit_schema() -> str:
    """
    Get the schema of EKS audit logs

    Returns:
        JSON string describing the audit log schema
    """
    schema = {
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
                "groups": "List of user groups"
            },
            "sourceIPs": "List of source IP addresses",
            "userAgent": "User agent string",
            "objectRef": {
                "resource": "Resource type (pods, services, deployments, etc.)",
                "namespace": "Kubernetes namespace",
                "name": "Resource name",
                "apiVersion": "API version"
            },
            "responseStatus": {
                "code": "HTTP response code",
                "status": "Response status"
            },
            "requestReceivedTimestamp": "When the request was received",
            "stageTimestamp": "Timestamp for this stage",
            "annotations": "Additional annotations"
        }
    }

    return json.dumps(schema, indent=2)


@mcp.tool()
def execute_custom_sql(sql_query: str) -> str:
    """
    Execute a custom DuckDB SQL query against EKS audit logs

    Args:
        sql_query: DuckDB SQL query (use read_json_auto() to read from S3)

    Returns:
        JSON string with query results

    Warning:
        Be careful with this tool - it allows arbitrary SQL execution
    """
    try:
        results = query_engine.execute_query(sql_query)

        return json.dumps({
            'status': 'success',
            'query': sql_query,
            'count': len(results),
            'results': results
        }, indent=2)

    except Exception as e:
        return json.dumps({
            'status': 'error',
            'error': str(e),
            'query': sql_query
        }, indent=2)


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
