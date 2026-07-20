"""The guided tour: an ordered registry of predefined DuckDB actions.

Each action carries the SQL it runs, a description shown before running,
and a `teaches` blurb shown next to the result. The order tells a story:
ingest -> query files in place -> analyze -> mutate -> materialize -> internals.
"""

ACTIONS = [
    {
        "id": "ingest-csv",
        "title": "1. Ingest a CSV into a table",
        "category": "ingest",
        "description": (
            "DuckDB treats files as if they were tables. read_csv_auto sniffs the "
            "header, delimiters and column types for you — no schema declaration needed."
        ),
        "sql": "CREATE OR REPLACE TABLE sales AS\nSELECT * FROM read_csv_auto('data/sales.csv');",
        "teaches": (
            "One statement turned a raw CSV into a typed, queryable table. Check the "
            "DB State panel: `sales` now exists with an inferred schema (dates became "
            "DATE, amounts became DOUBLE). This is the ingest path — the data now "
            "lives inside the .duckdb file."
        ),
    },
    {
        "id": "query-parquet",
        "title": "2. Query a Parquet file directly",
        "category": "ingest",
        "description": (
            "You don't have to ingest at all. DuckDB can run SQL straight against a "
            "Parquet (or CSV, or JSON) file path as if it were a table."
        ),
        "sql": (
            "SELECT category, count(*) AS n, round(avg(price), 2) AS avg_price\n"
            "FROM 'data/products.parquet'\n"
            "GROUP BY category ORDER BY n DESC;"
        ),
        "teaches": (
            "Notice the DB State panel did NOT change — no table was created, no data "
            "was copied. DuckDB scanned the Parquet file in place, reading only the "
            "columns the query needed (Parquet is columnar, like DuckDB itself)."
        ),
    },
    {
        "id": "aggregate",
        "title": "3. OLAP aggregation (GROUP BY)",
        "category": "analyze",
        "description": (
            "The classic analytical query: summarize millions of rows into a few. "
            "This is the workload columnar storage and vectorized execution are built for."
        ),
        "sql": (
            "SELECT region,\n"
            "       date_trunc('month', order_date) AS month,\n"
            "       round(sum(amount), 2) AS revenue,\n"
            "       count(*) AS orders\n"
            "FROM sales\n"
            "GROUP BY region, month\n"
            "ORDER BY month, region;"
        ),
        "teaches": (
            "This query touched only 3 of the 7 columns in `sales`. A row store would "
            "still read every byte of every row; DuckDB's columnar engine reads just "
            "the columns involved — exactly the animation from the Learn page."
        ),
    },
    {
        "id": "window",
        "title": "4. Window functions",
        "category": "analyze",
        "description": (
            "Analytical SQL beyond GROUP BY: running totals and rankings computed "
            "over partitions of the data, without collapsing the rows."
        ),
        "sql": (
            "WITH monthly AS (\n"
            "  SELECT region, date_trunc('month', order_date) AS month,\n"
            "         round(sum(amount), 2) AS revenue\n"
            "  FROM sales GROUP BY region, month\n"
            ")\n"
            "SELECT region, month, revenue,\n"
            "       round(sum(revenue) OVER (PARTITION BY region ORDER BY month), 2)\n"
            "         AS running_total,\n"
            "       rank() OVER (PARTITION BY month ORDER BY revenue DESC)\n"
            "         AS rank_in_month\n"
            "FROM monthly\n"
            "ORDER BY month, region;"
        ),
        "teaches": (
            "Each row keeps its identity while gaining context from its neighbors: a "
            "cumulative total per region, and a rank within its month. Window "
            "functions are a hallmark of analytical (OLAP) SQL engines."
        ),
    },
    {
        "id": "join-files",
        "title": "5. Join a table with a raw file",
        "category": "analyze",
        "description": (
            "The two worlds compose: join the ingested `sales` table against the "
            "products.parquet file — one lives in the database, one on disk."
        ),
        "sql": (
            "SELECT p.category, round(sum(s.amount), 2) AS revenue\n"
            "FROM sales s\n"
            "JOIN 'data/products.parquet' p USING (product_id)\n"
            "GROUP BY p.category\n"
            "ORDER BY revenue DESC;"
        ),
        "teaches": (
            "SQL over anything: tables, files, even remote URLs can all appear in the "
            "same query. This is why DuckDB is so popular for ETL and data wrangling — "
            "no loading ceremony before you can start joining."
        ),
    },
    {
        "id": "mutate",
        "title": "6. UPDATE and DELETE",
        "category": "mutate",
        "description": (
            "DuckDB is not read-only analytics — it is a real transactional (ACID) "
            "database. Apply a 10% price adjustment to EMEA and purge micro-orders."
        ),
        "sql": (
            "UPDATE sales SET amount = round(amount * 1.10, 2) WHERE region = 'EMEA';\n"
            "DELETE FROM sales WHERE amount < 20;"
        ),
        "teaches": (
            "Watch the DB State panel: the row count of `sales` just dropped. Both "
            "statements ran transactionally against the columnar store. (OLTP-style "
            "single-row churn isn't DuckDB's sweet spot, but correctness is fully there.)"
        ),
    },
    {
        "id": "ctas",
        "title": "7. Materialize a summary table (CTAS)",
        "category": "mutate",
        "description": (
            "CREATE TABLE AS SELECT: persist the result of an analysis as a new "
            "table — a tiny data mart inside your database file."
        ),
        "sql": (
            "CREATE OR REPLACE TABLE regional_summary AS\n"
            "SELECT region, round(sum(amount), 2) AS total_revenue, count(*) AS orders\n"
            "FROM sales GROUP BY region;"
        ),
        "teaches": (
            "A new table `regional_summary` just appeared in the DB State panel — "
            "derived data materialized from a query. Pipelines are often chains of "
            "exactly this: read files -> transform -> CTAS -> export."
        ),
    },
    {
        "id": "explain",
        "title": "8. Look inside: EXPLAIN",
        "category": "internals",
        "description": (
            "Ask DuckDB how it will execute a query. The plan is a tree of vectorized "
            "operators that data flows through, bottom to top."
        ),
        "sql": "EXPLAIN SELECT region, avg(amount) FROM sales GROUP BY region;",
        "teaches": (
            "Read bottom-up: SEQ_SCAN reads `sales` — note its Projections list only "
            "`region` and `amount`, the two columns the query touches (projection "
            "pushdown, the columnar win). Above it, HASH_GROUP_BY aggregates. Each "
            "operator processes ~2048-row vectors at a time — the vectorized execution "
            "from the Learn page, visible in the flesh."
        ),
    },
]

BY_ID = {a["id"]: a for a in ACTIONS}
