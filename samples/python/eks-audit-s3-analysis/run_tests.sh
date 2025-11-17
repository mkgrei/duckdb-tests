#!/bin/bash
# Test runner script for EKS Audit Log Analyzer

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}EKS Audit Log Analyzer - Test Runner${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}>>> $1${NC}\n"
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Please run: pip install -r requirements.txt"
    exit 1
fi

# Parse command line arguments
TEST_TYPE=${1:-all}

case $TEST_TYPE in
    unit)
        print_header "Running Unit Tests Only"
        pytest -v -m unit tests/
        ;;

    integration)
        print_header "Running Integration Tests Only"
        pytest -v -m integration tests/
        ;;

    fast)
        print_header "Running Fast Tests (Unit Tests)"
        pytest -v -m unit tests/
        ;;

    coverage)
        print_header "Running Tests with Coverage Report"
        pytest -v --cov=. --cov-report=html --cov-report=term tests/
        echo -e "\n${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;

    parsers)
        print_header "Running Parser Tests"
        pytest -v tests/test_parsers.py
        ;;

    engine)
        print_header "Running Query Engine Tests"
        pytest -v tests/test_query_engine.py
        ;;

    api)
        print_header "Running HTTP API Tests"
        pytest -v tests/test_http_api.py
        ;;

    mcp)
        print_header "Running MCP Tools Tests"
        pytest -v tests/test_mcp_tools.py
        ;;

    all)
        print_header "Running All Tests"
        pytest -v tests/
        ;;

    ci)
        print_header "Running CI Test Suite"
        pytest -v --cov=. --cov-report=xml --cov-report=term -m "not requires_s3" tests/
        ;;

    help)
        echo "Usage: ./run_tests.sh [TEST_TYPE]"
        echo ""
        echo "Available test types:"
        echo "  unit         - Run unit tests only (fast)"
        echo "  integration  - Run integration tests only"
        echo "  fast         - Run fast tests (alias for unit)"
        echo "  coverage     - Run tests with coverage report"
        echo "  parsers      - Run parser tests only"
        echo "  engine       - Run query engine tests only"
        echo "  api          - Run HTTP API tests only"
        echo "  mcp          - Run MCP tools tests only"
        echo "  all          - Run all tests (default)"
        echo "  ci           - Run CI test suite (excludes S3 tests)"
        echo "  help         - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh unit"
        echo "  ./run_tests.sh coverage"
        echo "  ./run_tests.sh api"
        ;;

    *)
        echo -e "${RED}Error: Unknown test type '$TEST_TYPE'${NC}"
        echo "Run './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}\n"
else
    echo -e "\n${RED}✗ Some tests failed${NC}\n"
fi

exit $EXIT_CODE
