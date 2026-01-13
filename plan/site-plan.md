# Patitas Documentation Site Plan

**Status**: Planning  
**Based on**: Kida and Rosettes site patterns

---

## Overview

Build a Bengal-powered documentation site for Patitas with GitHub Pages deployment.

**URL**: `https://lbliii.github.io/patitas`

---

## Directory Structure

```
patitas/
├── .github/
│   └── workflows/
│       ├── tests.yml      # CI: tests, lint, typecheck
│       └── pages.yml      # Deploy to GitHub Pages
├── site/
│   ├── assets/
│   │   └── fonts/         # Custom fonts (optional)
│   ├── config/
│   │   ├── _default/
│   │   │   ├── autodoc.yaml
│   │   │   ├── build.yaml
│   │   │   ├── content.yaml
│   │   │   ├── external_refs.yaml
│   │   │   ├── fonts.yaml
│   │   │   ├── outputs.yaml
│   │   │   ├── params.yaml
│   │   │   ├── search.yaml
│   │   │   ├── site.yaml
│   │   │   └── theme.yaml
│   │   └── environments/
│   │       ├── local.yaml
│   │       └── production.yaml
│   └── content/
│       ├── _index.md              # Home page
│       ├── docs/
│       │   ├── _index.md          # Docs landing
│       │   ├── get-started/
│       │   │   ├── _index.md
│       │   │   ├── installation.md
│       │   │   └── quickstart.md
│       │   ├── syntax/            # Markdown syntax
│       │   │   ├── _index.md
│       │   │   ├── inline.md
│       │   │   ├── blocks.md
│       │   │   ├── links.md
│       │   │   └── code.md
│       │   ├── directives/        # MyST directives
│       │   │   ├── _index.md
│       │   │   ├── admonition.md
│       │   │   ├── container.md
│       │   │   ├── dropdown.md
│       │   │   └── tabs.md
│       │   ├── extending/
│       │   │   ├── _index.md
│       │   │   ├── custom-directives.md
│       │   │   └── plugins.md
│       │   ├── reference/
│       │   │   ├── _index.md
│       │   │   ├── api.md
│       │   │   └── nodes.md
│       │   ├── about/
│       │   │   ├── _index.md
│       │   │   ├── architecture.md
│       │   │   ├── performance.md
│       │   │   └── thread-safety.md
│       │   └── troubleshooting/
│       │       ├── _index.md
│       │       └── common-errors.md
│       └── releases/
│           ├── _index.md
│           └── 0.1.0.md
└── pyproject.toml                 # Add docs = ["bengal>=0.1.8"]
```

---

## Configuration Files

### site/config/_default/site.yaml

```yaml
# Patitas Documentation Site Configuration
site:
  title: "Patitas"
  logo_text: "ฅᨐฅ"
  description: "Modern Markdown parser for Python 3.14t"
  language: "en"

template_engine: kida
```

### site/config/_default/params.yaml

```yaml
params:
  project_status: "beta"
  repo_url: "https://github.com/lbliii/patitas"
  min_python: "3.14"
```

### site/config/_default/autodoc.yaml

```yaml
autodoc:
  github_repo: "lbliii/patitas"
  github_branch: "main"

  python:
    enabled: true
    source_dirs:
      - ../src/patitas
    docstring_style: auto
    output_prefix: "api"
    display_name: "Patitas API Reference"
    exclude:
      - "*/tests/*"
      - "*/test_*.py"
      - "*/__pycache__/*"
      - "*/.venv/*"
    include_private: false
    include_special: false

  cli:
    enabled: false

  openapi:
    enabled: false
```

### site/config/_default/theme.yaml

```yaml
theme:
  name: "default"
  default_appearance: "light"
  default_palette: "brown-bengal"

  syntax_highlighting:
    theme: "auto"
    css_class_style: "semantic"

  features:
    - navigation.breadcrumbs
    - navigation.toc
    - navigation.toc.sticky
    - navigation.prev_next
    - navigation.back_to_top
    - content.code.copy
    - content.reading_time
    - graph.contextual
    - search
    - search.suggest
    - search.highlight
    - accessibility.skip_link

  max_tags_display: 10
  popular_tags_count: 20
```

### site/config/_default/content.yaml

```yaml
markdown:
  parser: "patitas"  # Dogfooding!

content:
  default_type: "doc"
  excerpt_length: 200
  summary_length: 160
  reading_speed: 200
  related_count: 5
  related_threshold: 0.25
  toc_depth: 4
  toc_min_headings: 2
  toc_style: "nested"
  sort_pages_by: "weight"
  sort_order: "asc"
```

### site/config/_default/build.yaml

```yaml
build:
  output_dir: "public"
  incremental: true

build_badge:
  enabled: true

assets:
  minify: true
  fingerprint: true

html_output:
  mode: "pretty"
  remove_comments: true
  collapse_blank_lines: true

health_check:
  enabled: true
  verbose: false
```

### site/config/environments/production.yaml

```yaml
site:
  baseurl: "/patitas"

build:
  incremental: true
  strict_mode: true

assets:
  minify: true
  fingerprint: true
```

### site/config/environments/local.yaml

```yaml
site:
  baseurl: ""

build:
  incremental: true
  strict_mode: false

assets:
  minify: false
  fingerprint: false
```

---

## GitHub Workflows

### .github/workflows/pages.yml

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          python-version: "3.14t"

      - name: Cache uv dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
          restore-keys: |
            uv-${{ runner.os }}-

      - name: Install dependencies
        run: uv sync --group dev --group docs
        env:
          PYTHON_GIL: "0"

      - name: Get cache hash
        id: cache
        working-directory: site
        run: echo "hash=$(uv run bengal cache hash)" >> $GITHUB_OUTPUT
        env:
          PYTHON_GIL: "0"

      - name: Cache Bengal build state
        uses: actions/cache@v4
        with:
          path: site/.bengal
          key: bengal-${{ runner.os }}-${{ steps.cache.outputs.hash }}

      - name: Build documentation site
        working-directory: site
        run: uv run bengal site build --environment production
        env:
          PYTHON_GIL: "0"

      - name: Prepare for upload
        run: |
          touch site/public/.nojekyll
          echo "" > site/public/.gitignore

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: site/public

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    needs: build
    runs-on: ubuntu-latest
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

### .github/workflows/tests.yml

```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 0'
  workflow_dispatch:

concurrency:
  group: tests-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.14t"]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Cache uv dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
          restore-keys: |
            uv-${{ runner.os }}-

      - name: Install dependencies
        run: uv sync --group dev

      - name: Run tests
        env:
          CI: true
          PYTHON_GIL: "0"
        run: |
          uv run pytest -n auto -q --tb=short --dist worksteal

      - name: Run tests with coverage
        if: matrix.python-version == '3.14t'
        env:
          CI: true
          PYTHON_GIL: "0"
        run: |
          uv run pytest -n 0 -q --tb=short --cov=patitas --cov-report=xml

      - name: Upload coverage to Codecov
        if: matrix.python-version == '3.14t'
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
          fail_ci_if_error: false

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          python-version: "3.14t"

      - name: Cache uv dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
          restore-keys: |
            uv-${{ runner.os }}-

      - name: Install dependencies
        run: uv sync --group dev

      - name: Run pyright
        run: |
          uv run pyright src/patitas

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          python-version: "3.14t"

      - name: Cache uv dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
          restore-keys: |
            uv-${{ runner.os }}-

      - name: Install dependencies
        run: uv sync --group dev

      - name: Run ruff check
        run: |
          uv run ruff check src/patitas tests/

      - name: Run ruff format check
        run: |
          uv run ruff format --check src/patitas tests/

  commonmark-spec:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          python-version: "3.14t"

      - name: Cache uv dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
          restore-keys: |
            uv-${{ runner.os }}-

      - name: Install dependencies
        run: uv sync --group dev

      - name: Run CommonMark spec tests
        env:
          CI: true
          PYTHON_GIL: "0"
        run: |
          uv run pytest tests/test_commonmark_spec.py -v --tb=short
```

---

## pyproject.toml Updates

Add docs dependency group:

```toml
[dependency-groups]
dev = [
    "pytest>=8.3.5",
    "pytest-benchmark>=5.1.0",
    "pyright>=1.1.391",
    "pytest-xdist>=3.5.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.9.4",
]
docs = ["bengal>=0.1.8"]
```

---

## Content Plan

### Home Page (site/content/_index.md)

Key sections:
- Hero with `ฅᨐฅ` branding
- Why Patitas? (Fast, Safe, Modern, Standards-based, Zero dependencies)
- Quick Start code example
- Feature comparison table
- Performance benchmarks
- The Bengal Cat Family

### Docs Structure

| Section | Type | Description |
|---------|------|-------------|
| Get Started | Tutorial | Installation + Quickstart |
| Syntax | Reference | Markdown syntax (inline, blocks, links, code) |
| Directives | Reference | MyST directives (admonition, container, tabs, dropdown) |
| Extending | How-to | Custom directives, plugins |
| Reference | Reference | API docs, AST nodes |
| About | Explanation | Architecture, performance, thread-safety |
| Troubleshooting | How-to | Common errors and fixes |

---

## Implementation Tasks

1. [ ] Create `.github/workflows/` directory
2. [ ] Add `tests.yml` workflow
3. [ ] Add `pages.yml` workflow
4. [ ] Create `site/` directory structure
5. [ ] Add all config files
6. [ ] Create home page content
7. [ ] Create docs structure
8. [ ] Update `pyproject.toml` with docs group
9. [ ] Test local build with `bengal site build`
10. [ ] Enable GitHub Pages in repository settings

---

## Timeline

| Phase | Tasks | Estimate |
|-------|-------|----------|
| 1 | Workflows + config | 30 min |
| 2 | Core content (home, get-started) | 1 hour |
| 3 | Syntax + Directives docs | 2 hours |
| 4 | Reference + About | 1 hour |
| 5 | Test + Deploy | 30 min |

**Total**: ~5 hours

---

## Notes

- Uses Patitas as markdown parser (dogfooding)
- Uses Kida as template engine
- Uses Rosettes for syntax highlighting (optional extra)
- Follows Bengal ecosystem conventions
- Autodoc generates API reference from source
