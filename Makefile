# Patitas Development Makefile
# =============================================================================

.PHONY: help install dev test lint ty typecheck format clean build docs benchmark publish release

# Default target
help:
	@echo "Patitas Development Commands"
	@echo "============================"
	@echo ""
	@echo "Setup:"
	@echo "  make install     Install package in development mode"
	@echo "  make dev         Install with all dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test        Run all tests"
	@echo "  make test-fast   Run tests without slow markers"
	@echo "  make test-cov    Run tests with coverage"
	@echo "  make commonmark  Run CommonMark compliance tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint        Run ruff linter"
	@echo "  make ty          Run ty type checker (fast, Rust-based)"
	@echo "  make typecheck   Run mypy type checker (legacy)"
	@echo "  make format      Format code with ruff"
	@echo "  make check       Run all checks (lint + ty)"
	@echo ""
	@echo "Build & Release:"
	@echo "  make build       Build distribution packages"
	@echo "  make publish     Publish to PyPI (uses .env for token)"
	@echo "  make release     Build and publish in one step"
	@echo "  make clean       Remove build artifacts"
	@echo ""
	@echo "Benchmarks:"
	@echo "  make benchmark   Run performance benchmarks"

# =============================================================================
# Setup
# =============================================================================

install:
	uv pip install -e .

dev:
	uv sync --group dev

# =============================================================================
# Testing
# =============================================================================

test:
	uv run pytest tests/ -v

test-fast:
	uv run pytest tests/ -v -m "not slow"

test-cov:
	uv run pytest tests/ -v --cov=patitas --cov-report=term-missing

commonmark:
	uv run pytest tests/ -v -m "commonmark"

# =============================================================================
# Code Quality
# =============================================================================

lint:
	uv run ruff check src/ tests/

ty:
	@echo "Running ty type checker (Astral, Rust-based)..."
	uv run ty check src/patitas/

typecheck:
	@echo "Running mypy type checking (legacy)..."
	uv run mypy src/patitas/

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

check: lint ty

# =============================================================================
# Build & Release
# =============================================================================

build:
	@echo "Building distribution packages..."
	rm -rf dist/
	uv build
	@echo "✓ Built:"
	@ls -la dist/

publish:
	@echo "Publishing to PyPI..."
	@if [ -f .env ]; then \
		export $$(cat .env | xargs) && uv publish; \
	else \
		echo "Warning: No .env file found, trying without token..."; \
		uv publish; \
	fi

release: build publish
	@echo "✓ Release complete"

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# =============================================================================
# Benchmarks
# =============================================================================

benchmark:
	uv run pytest benchmarks/ -v --benchmark-only

# =============================================================================
# Verification (for extraction)
# =============================================================================

verify:
	@echo "Checking for Bengal imports..."
	@! grep -r "from bengal" src/patitas/ || (echo "ERROR: Found Bengal imports in core" && exit 1)
	@echo "✓ No Bengal imports found in core"
	@echo ""
	@echo "Running tests..."
	@uv run pytest tests/ -v
	@echo ""
	@echo "✓ Verification complete"
