# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Supypowers is a Python CLI tool that lets AI agents and developers run self-contained Python scripts as callable, schema-documented functions. Each script declares its own dependencies via `uv` inline script metadata, so there's no environment management needed. The CLI has zero runtime dependencies itself.

## Build & Test Commands

```bash
# Run all tests
uv run python -m unittest discover -s tests -p "test_*.py" -q

# Run a single test
uv run python -m unittest tests.test_cli.TestCLI.test_run_exponents_compute_sqrt

# Build sdist + wheel
python -m build

# Run the CLI locally
uv run supypowers skills
uv run supypowers run --examples exponents:compute_sqrt '{"x": 9}'
```

Requires `uv` on PATH. No linter or formatter is configured.

## Architecture

**Source layout:** `src/supypowers/` with four modules:

- **cli.py** (~1100 lines) — The core. Contains all CLI subcommands (`init`, `new`, `run`, `docs`, `skills`), embedded runner/docs Python code templates (`_RUNNER_CODE`, `_DOCS_CODE`), and script templates (`_HELLO_PY`, `_NEW_SCRIPT_TEMPLATE`). Entry point: `app()`.
- **uv_exec.py** — Executes code in isolated environments via `uv run --with <deps> python -c <code>`. Passes payloads via stdin as JSON. Returns `UVRunError` on failure.
- **uv_script_metadata.py** — Parses `# /// script` blocks from Python files to extract dependency lists using AST parsing.
- **util.py** — Path resolution, secrets parsing (inline `KEY=VAL` and `.env` files).

**Execution flow:** CLI parses args → resolves script path in `supypowers/` folder → extracts dependencies from `# /// script` block → `uv_exec` runs the function in an isolated subprocess → validates input via Pydantic → returns JSON (`{"ok": true, "data": ...}` or `{"ok": false, "error": "..."}`).

**The supypower contract:** Every function must take exactly one parameter named `input` typed as a Pydantic `BaseModel`. Dependencies go in the `# /// script` header. No `print()` (breaks JSON output). No `input()` (no interactive terminal).

## Examples Directory

`examples/powers/` contains 10 example scripts (crypto, dates, exponents, fetch, files, misc, scrape, shell, strings, text). These are used by tests via the `--examples` flag and serve as canonical patterns for writing new scripts. Shell demos are in `examples/demo_*.sh`.

## Key Design Decisions

- **Zero runtime dependencies** — the package itself has no deps; per-script deps are resolved at execution time by `uv`.
- **All output is JSON** — designed for machine/agent consumption.
- **`uv` is required** — not pip. Scripts run via `uv run` with inline dependency resolution.
- **Hatchling build backend** — configured in `pyproject.toml`. `.env` files are excluded from distribution.
- **unittest** (not pytest) — test suite is in `tests/test_cli.py`.
