.PHONY: help install run-http run-mcp examples test test-unit test-integration test-coverage test-all clean docker-build docker-run docker-stop

help:
	@echo "EKS Audit Log Analyzer - Available Commands"
	@echo "==========================================="
	@echo "install            - Install Python dependencies"
	@echo "run-http           - Run HTTP REST API server"
	@echo "run-mcp            - Run FastMCP server"
	@echo "examples           - Run example queries"
	@echo ""
	@echo "Testing:"
	@echo "  test             - Run all tests"
	@echo "  test-unit        - Run unit tests only (fast)"
	@echo "  test-integration - Run integration tests"
	@echo "  test-coverage    - Run tests with coverage report"
	@echo "  test-all         - Run all tests with verbose output"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build     - Build Docker image"
	@echo "  docker-run       - Run with Docker Compose"
	@echo "  docker-stop      - Stop Docker containers"
	@echo "  docker-logs      - Show Docker logs"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean            - Clean up generated files"

install:
	pip install -r requirements.txt

run-http:
	python http_server.py

run-mcp:
	python server.py

examples:
	python example_queries.py

test:
	./run_tests.sh all

test-unit:
	./run_tests.sh unit

test-integration:
	./run_tests.sh integration

test-coverage:
	./run_tests.sh coverage

test-all:
	pytest -v tests/

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
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -f coverage.xml
