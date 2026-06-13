# Acme Toolkit

[![CI](https://example.com/badge.svg)](https://example.com/ci) [![PyPI](https://img.shields.io/pypi/v/acme-toolkit.svg)](https://pypi.org/project/acme-toolkit/)

A small, dependency-free toolkit for wrangling configuration files. It reads
TOML, YAML, and JSON, merges them with predictable precedence, and validates the
result against a schema you define in plain Python.

## Why another config library?

Most config libraries either do too little (parse one format and stop) or too
much (pull in a web framework's worth of dependencies). Acme Toolkit aims for a
middle path: a focused core, a typed result, and no surprises.

- **Predictable merging** — later sources win, lists replace rather than append.
- **Typed access** — `config.get("port", int)` raises if the value is the wrong type.
- **Zero runtime dependencies** — the core ships as a single package.

## Installation

```bash
pip install acme-toolkit
```

Python 3.11 or newer is required.

## Quick start

```python
from acme import Config

config = (
    Config.from_file("defaults.toml")
    .merge_file("production.yaml")
    .merge_env(prefix="ACME_")
)

port = config.get("server.port", int)
debug = config.get("server.debug", bool, default=False)
```

Precedence runs from lowest to highest:

| Source            | Precedence | Notes                                  |
|-------------------|------------|----------------------------------------|
| Built-in defaults | lowest     | Defined in code                        |
| `defaults.toml`   | low        | Checked into the repo                  |
| `production.yaml` | medium     | Deployed alongside the app             |
| Environment       | highest    | `ACME_SERVER__PORT=8080`               |

## Validation

Define a schema once and reuse it:

```python
schema = {
    "server.port": int,
    "server.host": str,
    "features": list,
}
config.validate(schema)  # raises ConfigError on the first mismatch
```

> **Note**
> Validation is eager by default. Pass `lazy=True` to defer it until first access
> if you only touch a subset of keys.

## Contributing

Pull requests are welcome. Please run the test suite (`pytest`) and the linter
(`ruff check`) before opening one. See [CONTRIBUTING](CONTRIBUTING.md) for the
full guidelines, and open an issue first for anything larger than a bug fix.

## License

Released under the MIT License. See [LICENSE](LICENSE) for details.
