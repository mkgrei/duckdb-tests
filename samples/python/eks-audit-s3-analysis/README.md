# EKS Audit Log S3 Analysis with DuckDB

A comprehensive Python server for analyzing EKS (Elastic Kubernetes Service) audit logs stored in S3 using DuckDB. This sample demonstrates the power of DuckDB for direct S3 querying with multiple query interfaces.

## Features

- **Direct S3 Querying**: Query EKS audit logs directly from S3 without downloading
- **Multiple Query Interfaces**:
  - FastMCP tools for MCP integration
  - REST API endpoints
  - Grafana Loki-compatible queries
  - AI agent natural language queries
  - Custom SQL queries
- **High Performance**: Leverages DuckDB's columnar execution engine
- **Flexible**: Support for various query patterns and use cases

## Architecture

```
┌─────────────────┐
│   S3 Bucket     │
│ (EKS Audit Logs)│
└────────┬────────┘
         │
         │ DuckDB HTTPFS Extension
         │
┌────────▼─────────────────────────────────────┐
│          DuckDB Query Engine                 │
│  - S3 Integration                            │
│  - JSON Processing                           │
│  - Columnar Execution                        │
└────────┬─────────────────────────────────────┘
         │
         ├─────────────┬──────────────┬─────────┐
         │             │              │         │
    ┌────▼───┐  ┌─────▼─────┐  ┌────▼────┐  ┌─▼──┐
    │ FastMCP│  │  Loki API │  │ AI Agent│  │ SQL│
    │  Tools │  │ Endpoint  │  │  Query  │  │API │
    └────────┘  └───────────┘  └─────────┘  └────┘
```

## Installation

### Prerequisites

- Python 3.8+
- AWS credentials with S3 access
- EKS audit logs stored in S3

### Setup

1. Clone or navigate to this directory:

```bash
cd samples/python/eks-audit-s3-analysis
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment:

```bash
cp .env.example .env
# Edit .env with your AWS credentials and S3 bucket information
```

## Configuration

Edit `.env` file with your settings:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# S3 Configuration
S3_BUCKET=your-eks-audit-logs-bucket
S3_PREFIX=eks-audit-logs/

# Server Configuration
HOST=0.0.0.0
PORT=8000

# DuckDB Configuration
DUCKDB_MEMORY_LIMIT=4GB
DUCKDB_THREADS=4
```

## Usage

### 1. FastMCP Server (for MCP Integration)

Start the FastMCP server:

```bash
python server.py
```

Available MCP tools:

- `query_eks_audit_logs`: Basic query with filters
- `loki_style_query`: Grafana Loki-compatible queries
- `ai_agent_query`: Natural language queries
- `get_eks_audit_schema`: Get audit log schema
- `execute_custom_sql`: Execute custom DuckDB SQL

### 2. HTTP REST API Server

Start the HTTP server:

```bash
python http_server.py
```

The server will start on `http://localhost:8000` with interactive API docs at `/docs`.

### 3. Example Queries

Run the example queries:

```bash
python example_queries.py
```

## Query Examples

### Basic Query

Query all create operations:

```bash
curl "http://localhost:8000/query?verb=create&limit=10"
```

### Namespace Filter

Query events in production namespace:

```bash
curl "http://localhost:8000/query?namespace=production&limit=20"
```

### Time Range Query

Query events in the last 24 hours:

```bash
curl "http://localhost:8000/query?start_time=2024-01-15T00:00:00Z&end_time=2024-01-16T00:00:00Z"
```

### Loki-Style Query

```bash
curl -X POST http://localhost:8000/loki/api/v1/query_range \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{namespace=\"kube-system\",verb=\"update\"}",
    "start": 1705320000000000000,
    "end": 1705323600000000000,
    "limit": 1000
  }'
```

### AI Agent Query

```bash
curl -X POST http://localhost:8000/ai/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me all failed pod creations in the last hour",
    "time_range": "1h"
  }'
```

### Custom SQL Query

```bash
curl -X POST http://localhost:8000/sql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT verb, COUNT(*) as count FROM read_json_auto('\''s3://your-bucket/eks-audit-logs/*.json'\'') GROUP BY verb"
  }'
```

### Statistics

Get aggregated statistics:

```bash
curl "http://localhost:8000/stats?time_range=24h"
```

## EKS Audit Log Schema

EKS audit logs follow the Kubernetes audit log format:

```json
{
  "timestamp": "2024-01-15T10:30:00.234567Z",
  "level": "RequestResponse",
  "auditID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
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
    "code": 201
  }
}
```

## Common Use Cases

### 1. Security Auditing

Find all failed authentication/authorization attempts:

```sql
SELECT
  timestamp,
  user_username,
  verb,
  objectRef_namespace,
  responseStatus_code,
  sourceIPs
FROM read_json_auto('s3://bucket/eks-audit-logs/*.json')
WHERE responseStatus_code >= 400
ORDER BY timestamp DESC
LIMIT 100
```

### 2. Compliance Reporting

Generate daily statistics:

```sql
SELECT
  DATE_TRUNC('day', CAST(timestamp AS TIMESTAMP)) as day,
  verb,
  COUNT(*) as operation_count,
  COUNT(DISTINCT user_username) as unique_users
FROM read_json_auto('s3://bucket/eks-audit-logs/*.json')
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 30 DAY
GROUP BY day, verb
ORDER BY day DESC
```

### 3. User Activity Tracking

Track specific user actions:

```sql
SELECT
  timestamp,
  verb,
  objectRef_namespace,
  objectRef_resource,
  objectRef_name,
  responseStatus_code
FROM read_json_auto('s3://bucket/eks-audit-logs/*.json')
WHERE user_username = 'john.doe'
ORDER BY timestamp DESC
LIMIT 50
```

### 4. Resource Deletion Tracking

Monitor all delete operations:

```sql
SELECT
  timestamp,
  user_username,
  objectRef_namespace,
  objectRef_resource,
  objectRef_name,
  responseStatus_code
FROM read_json_auto('s3://bucket/eks-audit-logs/*.json')
WHERE verb = 'delete'
  AND timestamp >= CURRENT_TIMESTAMP - INTERVAL 7 DAY
ORDER BY timestamp DESC
```

### 5. Privileged Access Monitoring

Track access to sensitive resources:

```sql
SELECT
  timestamp,
  user_username,
  verb,
  objectRef_namespace,
  objectRef_name
FROM read_json_auto('s3://bucket/eks-audit-logs/*.json')
WHERE objectRef_namespace = 'kube-system'
   OR objectRef_resource IN ('secrets', 'configmaps')
ORDER BY timestamp DESC
LIMIT 100
```

## Integration with Grafana

This server can be integrated with Grafana using the Loki data source:

1. Add a Loki data source in Grafana
2. Point it to `http://localhost:8000/loki`
3. Use LogQL syntax to query your EKS audit logs

Example Grafana queries:

- `{namespace="production"}` - All events in production
- `{verb="delete"}` - All delete operations
- `{namespace="kube-system",verb="update"}` - Updates in kube-system
- `{verb="create"} |= "error"` - Failed create operations

## Performance Considerations

### DuckDB Optimizations

1. **Memory Limit**: Adjust `DUCKDB_MEMORY_LIMIT` based on your system
2. **Thread Count**: Set `DUCKDB_THREADS` to match your CPU cores
3. **Partitioning**: Organize S3 logs by date for faster queries

### S3 Best Practices

1. **Partitioning**: Use date-based prefixes (e.g., `logs/2024/01/15/`)
2. **File Size**: Keep JSON files between 10-100 MB for optimal performance
3. **Compression**: Use gzip compression to reduce data transfer
4. **Lifecycle**: Archive old logs to S3 Glacier

### Query Optimization

1. **Time Range**: Always specify a time range to limit data scanned
2. **Projections**: Select only needed columns
3. **Filters**: Push down filters to reduce data processing
4. **Aggregations**: Use DuckDB's built-in aggregation functions

Example optimized query:

```sql
SELECT
  DATE_TRUNC('hour', CAST(timestamp AS TIMESTAMP)) as hour,
  verb,
  COUNT(*) as count
FROM read_json_auto('s3://bucket/logs/2024/01/15/*.json.gz')
WHERE timestamp >= '2024-01-15T00:00:00Z'
  AND timestamp < '2024-01-16T00:00:00Z'
  AND verb IN ('create', 'delete', 'update')
GROUP BY hour, verb
ORDER BY hour DESC
```

## Troubleshooting

### AWS Credentials

If you get authentication errors:

1. Verify your AWS credentials are correct
2. Check IAM permissions for S3 access
3. Ensure the S3 bucket name and region are correct

### DuckDB Extensions

If extensions fail to load:

```python
# Manually install extensions
python -c "import duckdb; conn = duckdb.connect(); conn.execute('INSTALL httpfs'); conn.execute('INSTALL json')"
```

### Memory Issues

If you run out of memory:

1. Reduce `DUCKDB_MEMORY_LIMIT`
2. Decrease query `LIMIT`
3. Add more specific filters
4. Query smaller time ranges

## Security Considerations

### AWS Credentials

- Never commit `.env` file to version control
- Use IAM roles when running on AWS infrastructure
- Implement least-privilege access for S3 buckets

### Query Restrictions

- Limit custom SQL queries to trusted users
- Implement query timeouts
- Monitor resource usage
- Consider implementing query result size limits

### API Security

For production deployment:

1. Add authentication (OAuth2, API keys)
2. Implement rate limiting
3. Enable HTTPS
4. Add request validation
5. Implement audit logging

## Advanced Features

### Custom Aggregations

Create custom views for common queries:

```sql
CREATE VIEW failed_operations AS
SELECT
  timestamp,
  user_username,
  verb,
  objectRef_namespace,
  objectRef_resource,
  responseStatus_code
FROM read_json_auto('s3://bucket/logs/*.json')
WHERE responseStatus_code >= 400;
```

### Joining with Other Data

Join audit logs with other data sources:

```sql
SELECT
  a.timestamp,
  a.user_username,
  u.department,
  a.verb,
  a.objectRef_namespace
FROM read_json_auto('s3://bucket/logs/*.json') a
LEFT JOIN read_csv_auto('s3://bucket/users.csv') u
  ON a.user_username = u.username
WHERE a.timestamp >= CURRENT_TIMESTAMP - INTERVAL 24 HOUR
```

### Time Series Analysis

Analyze trends over time:

```sql
SELECT
  DATE_TRUNC('hour', CAST(timestamp AS TIMESTAMP)) as hour,
  verb,
  COUNT(*) as event_count,
  AVG(CASE WHEN responseStatus_code >= 400 THEN 1.0 ELSE 0.0 END) as error_rate
FROM read_json_auto('s3://bucket/logs/*.json')
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 7 DAY
GROUP BY hour, verb
ORDER BY hour DESC, event_count DESC
```

## Testing with Sample Data

Use the included `example_data.json` for local testing:

```bash
# Start the server
python http_server.py

# In another terminal, load sample data
# Update server.py to point to local file instead of S3:
# s3_path = 'example_data.json'

# Test queries
curl "http://localhost:8000/query?limit=5"
```

## Next Steps

1. **Integrate with Claude Desktop**: Use the FastMCP server with Claude Desktop MCP
2. **Add Authentication**: Implement OAuth2 or API key authentication
3. **Create Dashboards**: Build Grafana dashboards for visualization
4. **Set Up Alerts**: Configure alerting for security events
5. **Scale Horizontally**: Deploy multiple instances behind a load balancer

## Resources

- [DuckDB Documentation](https://duckdb.org/docs/)
- [DuckDB S3 Extension](https://duckdb.org/docs/extensions/httpfs.html)
- [Kubernetes Audit Logs](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)
- [EKS Audit Logging](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [FastMCP](https://github.com/jlowin/fastmcp)

## License

This example is provided as-is for educational purposes.

## Contributing

Feel free to extend this example with additional features:

- Additional query parsers (Prometheus, CloudWatch Insights, etc.)
- More sophisticated AI query translation
- Caching layer for frequently accessed data
- Real-time streaming support
- Advanced visualization options
