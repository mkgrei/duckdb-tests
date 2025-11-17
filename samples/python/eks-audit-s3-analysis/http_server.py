#!/usr/bin/env python3
"""
HTTP Server wrapper for EKS Audit Log Analyzer

Provides REST API endpoints for:
1. Grafana Loki-style queries
2. AI agent natural language queries
3. Direct SQL queries
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import the query engine from server.py
import sys
sys.path.append(os.path.dirname(__file__))
from server import (
    DuckDBQueryEngine,
    LokiQueryParser,
    AIQueryTranslator,
    LokiQueryRequest,
    AIAgentQueryRequest
)

# Initialize FastAPI app
app = FastAPI(
    title="EKS Audit Log Analyzer API",
    description="REST API for querying EKS audit logs from S3 using DuckDB",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize query engine
query_engine = DuckDBQueryEngine()


class QueryResponse(BaseModel):
    """Standard query response"""
    status: str
    count: int
    results: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response"""
    status: str = "error"
    error: str
    details: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "EKS Audit Log Analyzer",
        "version": "1.0.0",
        "endpoints": {
            "/query": "Basic query endpoint",
            "/loki/api/v1/query_range": "Grafana Loki-compatible endpoint",
            "/ai/query": "AI agent natural language query endpoint",
            "/sql": "Custom SQL query endpoint",
            "/schema": "Get audit log schema"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/query", response_model=QueryResponse)
async def query_logs(
    start_time: Optional[str] = Query(None, description="Start time in ISO format"),
    end_time: Optional[str] = Query(None, description="End time in ISO format"),
    verb: Optional[str] = Query(None, description="Kubernetes verb"),
    namespace: Optional[str] = Query(None, description="Kubernetes namespace"),
    user: Optional[str] = Query(None, description="Username"),
    limit: int = Query(100, description="Maximum number of results", ge=1, le=10000)
):
    """
    Query EKS audit logs with basic filters

    Example: /query?verb=create&namespace=production&limit=50
    """
    try:
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

        return QueryResponse(
            status="success",
            count=len(results),
            results=results,
            metadata={
                "filters": filters,
                "start_time": start_time,
                "end_time": end_time
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/loki/api/v1/query_range", response_model=QueryResponse)
async def loki_query_range(request: LokiQueryRequest):
    """
    Grafana Loki-compatible query endpoint

    Example request:
    {
        "query": "{namespace=\"kube-system\",verb=\"create\"}",
        "start": 1705320000000000000,
        "end": 1705323600000000000,
        "limit": 1000
    }
    """
    try:
        # Parse LogQL query
        filters = LokiQueryParser.parse_logql(request.query)

        # Convert nanosecond timestamps to datetime
        start_time = datetime.fromtimestamp(request.start / 1e9)
        end_time = datetime.fromtimestamp(request.end / 1e9)

        # Remove special filters
        includes = filters.pop('_includes', [])
        excludes = filters.pop('_excludes', [])

        # Execute query
        results = query_engine.query_eks_logs(
            start_time=start_time,
            end_time=end_time,
            filters=filters,
            limit=request.limit
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

        return QueryResponse(
            status="success",
            count=len(results),
            results=results,
            metadata={
                "query": request.query,
                "start": request.start,
                "end": request.end,
                "direction": request.direction
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/query", response_model=QueryResponse)
async def ai_query(request: AIAgentQueryRequest):
    """
    AI agent natural language query endpoint

    Example request:
    {
        "question": "Show me all failed pod creations in the last hour",
        "time_range": "1h"
    }
    """
    try:
        # Translate question to query parameters
        translation = AIQueryTranslator.translate_question(
            request.question,
            request.time_range or "24h"
        )

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
            'unique_users': list(set(r.get('user_username', 'unknown') for r in results)),
            'time_range': request.time_range,
            'question': request.question
        }

        return QueryResponse(
            status="success",
            count=len(results),
            results=results[:100],  # Limit to first 100 for performance
            metadata={
                "question": request.question,
                "translation": translation,
                "summary": summary
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sql")
async def execute_sql(query: Dict[str, str]):
    """
    Execute custom SQL query

    Example request:
    {
        "query": "SELECT * FROM read_json_auto('s3://bucket/logs/*.json') LIMIT 10"
    }

    Warning: Use with caution - allows arbitrary SQL execution
    """
    try:
        sql_query = query.get("query")
        if not sql_query:
            raise HTTPException(status_code=400, detail="Missing 'query' field")

        results = query_engine.execute_query(sql_query)

        return {
            "status": "success",
            "query": sql_query,
            "count": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/schema")
async def get_schema():
    """Get EKS audit log schema"""
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

    return schema


@app.get("/stats")
async def get_stats(
    time_range: str = Query("24h", description="Time range (e.g., '1h', '24h', '7d')")
):
    """Get aggregated statistics for a time range"""
    try:
        # Calculate time range
        delta = LokiQueryParser.parse_time_range(time_range)
        end_time = datetime.utcnow()
        start_time = end_time - delta

        # Get all events in time range
        results = query_engine.query_eks_logs(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )

        # Calculate statistics
        stats = {
            "time_range": time_range,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_events": len(results),
            "by_verb": {},
            "by_namespace": {},
            "by_user": {},
            "by_status_code": {},
            "failed_operations": 0
        }

        for result in results:
            # Count by verb
            verb = result.get('verb', 'unknown')
            stats['by_verb'][verb] = stats['by_verb'].get(verb, 0) + 1

            # Count by namespace
            namespace = result.get('objectRef_namespace', 'unknown')
            stats['by_namespace'][namespace] = stats['by_namespace'].get(namespace, 0) + 1

            # Count by user
            user = result.get('user_username', 'unknown')
            stats['by_user'][user] = stats['by_user'].get(user, 0) + 1

            # Count by status code
            status_code = result.get('responseStatus_code', 0)
            stats['by_status_code'][str(status_code)] = stats['by_status_code'].get(str(status_code), 0) + 1

            # Count failed operations
            if status_code >= 400:
                stats['failed_operations'] += 1

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    print(f"Starting EKS Audit Log Analyzer HTTP Server on {host}:{port}")
    print(f"API documentation available at http://{host}:{port}/docs")

    uvicorn.run(app, host=host, port=port)
