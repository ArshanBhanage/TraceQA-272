#!/bin/bash

# Test runner script for TraceQA E2E tests
# Usage: ./run_tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
TEST_MARKER=""
VERBOSE=""
COVERAGE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-url)
            BACKEND_URL="$2"
            shift 2
            ;;
        --marker|-m)
            TEST_MARKER="-m $2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE="-v"
            shift
            ;;
        --coverage)
            COVERAGE="--cov=api --cov-report=html --cov-report=term"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --backend-url URL    Backend API URL (default: http://localhost:8000)"
            echo "  --marker, -m MARKER  Run tests with specific marker (e.g., e2e, integration, slow)"
            echo "  --verbose, -v        Verbose output"
            echo "  --coverage           Run with coverage report"
            echo "  --help, -h           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Run all tests"
            echo "  $0 --marker e2e                      # Run only E2E tests"
            echo "  $0 --marker 'not slow'                # Skip slow tests"
            echo "  $0 --coverage                        # Run with coverage"
            echo "  $0 --backend-url http://localhost:8001  # Use different backend URL"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if backend is accessible
echo -e "${YELLOW}Checking if backend is accessible at ${BACKEND_URL}...${NC}"
if curl -s -f "${BACKEND_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is accessible${NC}"
else
    echo -e "${RED}✗ Backend is not accessible at ${BACKEND_URL}${NC}"
    echo "Please ensure the backend server is running:"
    echo "  cd backend && uvicorn main:app --reload"
    exit 1
fi

# Change to backend directory
cd "$(dirname "$0")/.." || exit 1

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
echo ""

export BACKEND_URL="${BACKEND_URL}"

pytest tests/ \
    ${TEST_MARKER} \
    ${VERBOSE} \
    ${COVERAGE} \
    --tb=short

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All tests passed!${NC}"
    if [ -n "$COVERAGE" ]; then
        echo -e "${YELLOW}Coverage report generated in htmlcov/index.html${NC}"
    fi
    exit 0
else
    echo ""
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
