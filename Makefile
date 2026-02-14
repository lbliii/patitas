# Patitas Development Makefile
# =============================================================================

.PHONY: help install dev test lint ty format clean build docs benchmark publish release gh-release

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
	@echo "  make format      Format code with ruff"
	@echo "  make check       Run all checks (lint + ty)"
	@echo ""
	@echo "Build & Release:"
	@echo "  make build       Build distribution packages"
	@echo "  make publish     Publish to PyPI (uses .env for token)"
	@echo "  make release     Build and publish in one step"
	@echo "  make gh-release  Create GitHub release (triggers PyPI via workflow), uses site release notes"
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

# Create GitHub release from site release notes; triggers python-publish workflow → PyPI
# Strips YAML frontmatter (--- ... ---) from notes before passing to gh
gh-release:
	@VERSION=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	PROJECT=$$(grep '^name = ' pyproject.toml | sed 's/name = "\(.*\)"/\1/'); \
	NOTES="site/content/releases/$$VERSION.md"; \
	if [ ! -f "$$NOTES" ]; then echo "Error: $$NOTES not found"; exit 1; fi; \
	echo "Creating release v$$VERSION for $$PROJECT..."; \
	git push origin main 2>/dev/null || true; \
	git push origin v$$VERSION 2>/dev/null || true; \
	awk '/^---$$/{c++;next}c>=2' "$$NOTES" | gh release create v$$VERSION \
		--title "$$PROJECT $$VERSION" \
		-F -; \
	echo "✓ GitHub release v$$VERSION created (PyPI publish will run via workflow)"

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
