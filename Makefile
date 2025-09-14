.PHONY: help format lint typecheck test clean install dev smoke

help:
	@echo "Available targets:"
	@echo "  install    - Install production dependencies"
	@echo "  dev        - Install development dependencies"
	@echo "  format     - Format code with black and ruff"
	@echo "  lint       - Run linting checks with ruff"
	@echo "  typecheck  - Run type checking with mypy"
	@echo "  test       - Run tests with pytest"
	@echo "  smoke      - Run smoke tests against local server"
	@echo "  clean      - Remove build artifacts and caches"
	@echo "  run        - Start the development server"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

format:
	@echo "Running black formatter..."
	black --line-length 100 app/ tests/
	@echo "Running ruff formatter..."
	ruff format app/ tests/
	@echo "Running isort..."
	isort --profile black --line-length 100 app/ tests/

lint:
	@echo "Running ruff linter..."
	ruff check app/ tests/
	@echo "Running flake8..."
	flake8 --max-line-length 100 app/ tests/

typecheck:
	@echo "Running mypy type checker..."
	mypy app/ --ignore-missing-imports

test:
	@echo "Running pytest..."
	pytest tests/ -v

smoke:
	@echo "Running smoke tests..."
	bash tools/smoke_a2a.sh

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true

run:
	@echo "Starting development server..."
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload