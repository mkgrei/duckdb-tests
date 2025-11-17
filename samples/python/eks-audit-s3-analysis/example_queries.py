#!/usr/bin/env python3
"""
Example queries for EKS Audit Log Analysis

This file demonstrates various ways to query EKS audit logs using:
1. Direct DuckDB SQL
2. Loki-style queries
3. AI agent natural language queries
"""

import json
import httpx
from datetime import datetime, timedelta


class QueryExamples:
    """Example queries for the EKS Audit Log Analyzer"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def example_1_basic_query(self):
        """Example 1: Basic query for all create operations"""
        print("\n=== Example 1: Basic Query - All Create Operations ===")

        query = {
            "verb": "create",
            "limit": 10
        }

        print(f"Query: {json.dumps(query, indent=2)}")
        # In practice, you would call the MCP tool here
        print("This would return all create operations in the audit logs")

    def example_2_namespace_filter(self):
        """Example 2: Query with namespace filter"""
        print("\n=== Example 2: Namespace Filter - Production Events ===")

        query = {
            "namespace": "production",
            "limit": 20
        }

        print(f"Query: {json.dumps(query, indent=2)}")
        print("This would return all events in the production namespace")

    def example_3_time_range(self):
        """Example 3: Query with time range"""
        print("\n=== Example 3: Time Range Query ===")

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)

        query = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "limit": 50
        }

        print(f"Query: {json.dumps(query, indent=2)}")
        print("This would return all events in the last 24 hours")

    def example_4_user_activity(self):
        """Example 4: Track specific user activity"""
        print("\n=== Example 4: User Activity Tracking ===")

        query = {
            "user": "john.doe",
            "limit": 100
        }

        print(f"Query: {json.dumps(query, indent=2)}")
        print("This would return all actions performed by john.doe")

    def example_5_loki_style_basic(self):
        """Example 5: Loki-style query - Basic"""
        print("\n=== Example 5: Loki-Style Query - Basic ===")

        loki_query = '{namespace="kube-system",verb="update"}'
        time_range = "24h"

        print(f"Query: {loki_query}")
        print(f"Time Range: {time_range}")
        print("This would return all update operations in kube-system namespace")

    def example_6_loki_style_advanced(self):
        """Example 6: Loki-style query - Advanced with filters"""
        print("\n=== Example 6: Loki-Style Query - Advanced ===")

        loki_query = '{namespace="production",verb="delete"} |= "pod"'
        time_range = "1h"

        print(f"Query: {loki_query}")
        print(f"Time Range: {time_range}")
        print("This would return all pod deletions in production namespace in the last hour")

    def example_7_loki_exclude(self):
        """Example 7: Loki-style query with exclusions"""
        print("\n=== Example 7: Loki-Style Query - With Exclusions ===")

        loki_query = '{verb="create"} != "success"'
        time_range = "7d"

        print(f"Query: {loki_query}")
        print(f"Time Range: {time_range}")
        print("This would return failed create operations in the last 7 days")

    def example_8_ai_security_audit(self):
        """Example 8: AI agent - Security audit"""
        print("\n=== Example 8: AI Agent - Security Audit ===")

        question = "Show me all failed authentication or authorization attempts in the last 24 hours"
        time_range = "24h"

        print(f"Question: {question}")
        print(f"Time Range: {time_range}")
        print("The AI agent would translate this to appropriate filters and return results")

    def example_9_ai_user_investigation(self):
        """Example 9: AI agent - User investigation"""
        print("\n=== Example 9: AI Agent - User Investigation ===")

        question = "What did user john.doe do in namespace production?"
        time_range = "7d"

        print(f"Question: {question}")
        print(f"Time Range: {time_range}")
        print("The AI agent would extract user and namespace filters automatically")

    def example_10_ai_resource_tracking(self):
        """Example 10: AI agent - Resource tracking"""
        print("\n=== Example 10: AI Agent - Resource Tracking ===")

        question = "Find all delete operations on pods in the last hour"
        time_range = "1h"

        print(f"Question: {question}")
        print(f"Time Range: {time_range}")
        print("The AI agent would identify the verb and resource type")

    def example_11_custom_sql(self):
        """Example 11: Custom SQL query"""
        print("\n=== Example 11: Custom SQL Query ===")

        sql = """
        SELECT
            verb,
            objectRef_namespace as namespace,
            COUNT(*) as event_count,
            COUNT(DISTINCT user_username) as unique_users
        FROM read_json_auto('s3://your-bucket/eks-audit-logs/*.json')
        WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 24 HOUR
        GROUP BY verb, objectRef_namespace
        ORDER BY event_count DESC
        LIMIT 10
        """

        print(f"SQL Query:\n{sql}")
        print("This would return aggregated statistics by verb and namespace")

    def example_12_security_analysis(self):
        """Example 12: Security analysis - Failed operations"""
        print("\n=== Example 12: Security Analysis - Failed Operations ===")

        sql = """
        SELECT
            timestamp,
            user_username,
            verb,
            objectRef_namespace,
            objectRef_resource,
            responseStatus_code,
            sourceIPs
        FROM read_json_auto('s3://your-bucket/eks-audit-logs/*.json')
        WHERE responseStatus_code >= 400
            AND timestamp >= CURRENT_TIMESTAMP - INTERVAL 24 HOUR
        ORDER BY timestamp DESC
        LIMIT 100
        """

        print(f"SQL Query:\n{sql}")
        print("This would return all failed operations for security review")

    def example_13_privileged_access(self):
        """Example 13: Track privileged access"""
        print("\n=== Example 13: Privileged Access Tracking ===")

        sql = """
        SELECT
            timestamp,
            user_username,
            verb,
            objectRef_namespace,
            objectRef_name,
            requestURI
        FROM read_json_auto('s3://your-bucket/eks-audit-logs/*.json')
        WHERE objectRef_namespace = 'kube-system'
            OR objectRef_resource = 'secrets'
            OR objectRef_resource = 'configmaps'
        ORDER BY timestamp DESC
        LIMIT 50
        """

        print(f"SQL Query:\n{sql}")
        print("This would return privileged operations on sensitive resources")

    def example_14_compliance_report(self):
        """Example 14: Compliance reporting"""
        print("\n=== Example 14: Compliance Report ===")

        sql = """
        WITH daily_stats AS (
            SELECT
                DATE_TRUNC('day', CAST(timestamp AS TIMESTAMP)) as day,
                verb,
                COUNT(*) as operation_count,
                COUNT(DISTINCT user_username) as unique_users,
                COUNT(CASE WHEN responseStatus_code >= 400 THEN 1 END) as failed_operations
            FROM read_json_auto('s3://your-bucket/eks-audit-logs/*.json')
            WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 30 DAY
            GROUP BY day, verb
        )
        SELECT
            day,
            verb,
            operation_count,
            unique_users,
            failed_operations,
            ROUND(100.0 * failed_operations / operation_count, 2) as failure_rate
        FROM daily_stats
        ORDER BY day DESC, operation_count DESC
        """

        print(f"SQL Query:\n{sql}")
        print("This would generate a 30-day compliance report with failure rates")

    def run_all_examples(self):
        """Run all examples"""
        examples = [
            self.example_1_basic_query,
            self.example_2_namespace_filter,
            self.example_3_time_range,
            self.example_4_user_activity,
            self.example_5_loki_style_basic,
            self.example_6_loki_style_advanced,
            self.example_7_loki_exclude,
            self.example_8_ai_security_audit,
            self.example_9_ai_user_investigation,
            self.example_10_ai_resource_tracking,
            self.example_11_custom_sql,
            self.example_12_security_analysis,
            self.example_13_privileged_access,
            self.example_14_compliance_report
        ]

        print("=" * 80)
        print("EKS Audit Log Analysis - Query Examples")
        print("=" * 80)

        for example in examples:
            example()

        print("\n" + "=" * 80)
        print("For more information, see the README.md file")
        print("=" * 80)


if __name__ == "__main__":
    examples = QueryExamples()
    examples.run_all_examples()
