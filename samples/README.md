# DuckDB Samples

A collection of practical examples demonstrating DuckDB's capabilities across various use cases and programming languages.

## Overview

DuckDB is an in-process SQL OLAP database management system designed for analytical workloads. These samples showcase:

- Direct querying of cloud storage (S3, Azure Blob, GCS)
- Integration with various data formats (JSON, Parquet, CSV)
- High-performance analytics on large datasets
- Integration with different programming languages and frameworks

## Samples

### Python

#### 1. EKS Audit Log S3 Analysis

**Location**: `python/eks-audit-s3-analysis/`

A comprehensive server for analyzing EKS (Elastic Kubernetes Service) audit logs stored in S3.

**Features**:
- Direct S3 querying without downloading files
- FastMCP server for MCP integration
- REST API with multiple query interfaces:
  - Grafana Loki-compatible queries
  - AI agent natural language queries
  - Custom SQL queries
- Real-time analysis of Kubernetes audit events

**Use Cases**:
- Security auditing and compliance
- User activity tracking
- Resource deletion monitoring
- Failed operation analysis
- Privilege escalation detection

**Quick Start**:
```bash
cd python/eks-audit-s3-analysis
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your AWS credentials
python http_server.py
```

**Technologies**:
- DuckDB with S3 (httpfs) extension
- FastMCP for MCP integration
- FastAPI for REST endpoints
- Grafana Loki-compatible API

See the [detailed README](python/eks-audit-s3-analysis/README.md) for more information.

## Coming Soon

More samples will be added to demonstrate:

### Python
- Parquet file analysis and optimization
- Real-time log analysis from multiple sources
- Data lake querying with DuckDB
- Time series analysis at scale

### JavaScript/TypeScript
- Node.js integration examples
- Browser-based analytics with DuckDB-WASM
- Serverless function examples

### Go
- High-performance data processing
- CLI tools for data analysis

### Rust
- Embedded analytics applications
- Performance-critical use cases

## General Patterns

All samples follow these patterns:

1. **Minimal Setup**: Easy to get started with clear dependencies
2. **Real-world Use Cases**: Practical examples you can adapt
3. **Best Practices**: Demonstrates optimal DuckDB usage
4. **Documentation**: Comprehensive README with examples
5. **Testing**: Sample data and queries included

## DuckDB Key Features Demonstrated

### 1. Cloud Storage Integration

DuckDB can directly query data from cloud storage:

```sql
-- Query S3 directly
SELECT * FROM 's3://bucket/path/*.parquet';

-- Query Azure Blob Storage
SELECT * FROM 'azure://container/path/*.csv';

-- Query Google Cloud Storage
SELECT * FROM 'gs://bucket/path/*.json';
```

### 2. Multiple File Formats

Support for various data formats:

- JSON (with automatic schema detection)
- Parquet (columnar format)
- CSV (with various delimiters)
- Excel files
- And many more

### 3. SQL Analytics

Full SQL support with advanced features:

- Window functions
- CTEs (Common Table Expressions)
- JSON operations
- Array operations
- String operations
- Date/time functions

### 4. Performance

- Columnar storage and execution
- Vectorized query execution
- Parallel processing
- Optimized for OLAP workloads

## Requirements

Common requirements across samples:

- DuckDB (installed via package managers or pip)
- Cloud credentials (for S3/Azure/GCS samples)
- Python 3.8+ (for Python samples)
- Node.js 16+ (for JavaScript samples)
- Go 1.19+ (for Go samples)
- Rust 1.70+ (for Rust samples)

## Contributing

Feel free to contribute additional samples! Each sample should:

1. Solve a real-world problem
2. Include comprehensive documentation
3. Provide example data or clear instructions
4. Follow best practices
5. Be well-tested

## Resources

- [DuckDB Documentation](https://duckdb.org/docs/)
- [DuckDB Extensions](https://duckdb.org/docs/extensions/overview.html)
- [DuckDB SQL Reference](https://duckdb.org/docs/sql/introduction)
- [DuckDB Blog](https://duckdb.org/news/)

## License

These samples are provided as-is for educational purposes.

## Support

For issues specific to:
- DuckDB: [GitHub Issues](https://github.com/duckdb/duckdb/issues)
- These samples: Open an issue in this repository
