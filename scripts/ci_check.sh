#!/usr/bin/env bash
set -euo pipefail

echo "=== Running CI Checks ==="
echo

echo "1. Code formatting check..."
black --check --line-length 100 app/ tests/ || {
    echo "❌ Black formatting check failed. Run 'make format' to fix."
    exit 1
}
echo "✅ Black check passed"

echo
echo "2. Import sorting check..."
isort --check-only --profile black --line-length 100 app/ tests/ || {
    echo "❌ Import sorting check failed. Run 'make format' to fix."
    exit 1
}
echo "✅ Import sorting check passed"

echo
echo "3. Linting with ruff..."
ruff check app/ tests/ || {
    echo "❌ Ruff linting failed. Fix the issues above."
    exit 1
}
echo "✅ Ruff linting passed"

echo
echo "4. Type checking with mypy..."
mypy app/ --ignore-missing-imports || {
    echo "❌ Type checking failed. Fix the issues above."
    exit 1
}
echo "✅ Type checking passed"

echo
echo "5. Running tests..."
pytest tests/ -q || {
    echo "❌ Tests failed. Fix the failing tests."
    exit 1
}
echo "✅ All tests passed"

echo
echo "=== ✅ All CI checks passed! ==="