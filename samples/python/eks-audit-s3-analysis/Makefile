.PHONY: help install run-http run-mcp test docker-build docker-run docker-stop clean

help:
	@echo "EKS Audit Log Analyzer - Available Commands"
	@echo "==========================================="
	@echo "install        - Install Python dependencies"
	@echo "run-http       - Run HTTP REST API server"
	@echo "run-mcp        - Run FastMCP server"
	@echo "examples       - Run example queries"
	@echo "test           - Run tests (if available)"
	@echo "docker-build   - Build Docker image"
	@echo "docker-run     - Run with Docker Compose"
	@echo "docker-stop    - Stop Docker containers"
	@echo "docker-logs    - Show Docker logs"
	@echo "clean          - Clean up generated files"

install:
	pip install -r requirements.txt

run-http:
	python http_server.py

run-mcp:
	python server.py

examples:
	python example_queries.py

test:
	@echo "No tests configured yet"

docker-build:
	docker-compose build

docker-run:
	docker-compose up -d

docker-run-with-grafana:
	docker-compose --profile with-grafana up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
