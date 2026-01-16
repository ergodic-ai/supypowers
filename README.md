# supypowers

Run self-contained Python scripts (with `uv` script dependencies) as callable, schema-documented functions.

## What you can do with this

- **Run** a typed function in a script: validate/coerce JSON input with Pydantic, execute, emit JSON output.
- **Generate documentation** for all scripts in a folder as either **JSON** (for machines/LLMs) or **Markdown** (for humans).

## Prerequisites

- **`uv`** must be installed and on your `PATH` (the CLI shells out to `uv run`).

## Install

```bash
pip install supypowers
```

If you prefer installing via `uv` tools (to get a global `supypowers` command without a venv), see “Install `supypowers` on your PATH”.

## Quickstart

Try the bundled examples:

```bash
supypowers examples docs --format md
supypowers examples run exponents:compute_sqrt "{'x': 9}"
```

Initialize a new `supypowers/` folder with starter templates (`hello.py` + `hello.md`):

```bash
supypowers . init
```

If you don’t have the `supypowers` command on your PATH yet, you can always run it via `uv` from this repo:

```bash
uv run supypowers examples docs --format md
uv run supypowers examples run exponents:compute_sqrt "{'x': 9}"
```

## Core concepts

### Script dependencies (per-script, no venv)

Each script declares its dependencies using `uv` inline script metadata:

```bash
# /// script
# dependencies = [
#   "pydantic",
# ]
# ///
```

Supypowers reads those dependencies and runs your function in an isolated `uv run` environment (it **does not import your script into the CLI process**).

### Superpower function contract

A function is considered a “supypower” if it matches this contract:

- **Exactly one parameter**, named **`input`**
- The `input` type is a **Pydantic `BaseModel`**
- Input data is **validated/coerced** via Pydantic (it must be an object mapping)
- Output can be any type; if it’s a Pydantic model, it will be emitted in JSON-friendly form

See `examples/exponents.py` for the canonical pattern.

## Running functions

### Syntax

```bash
supypowers <folder> run <script>:<function> <input_data> [--secrets ...]
```

### Input format (`<input_data>`)

- **Preferred**: strict JSON (e.g. `{"x": 9}`)
- **Also supported** (“YAML-ish”): Python literal objects (e.g. `{'x': 9}`) via `ast.literal_eval`

Supypowers will then validate/coerce that object into your Pydantic model.

### Secrets (`--secrets`)

You can pass secrets as:

- a **dotenv file path** (e.g. `--secrets .env`)
- **inline** `KEY=VAL` pairs (e.g. `--secrets API_KEY=abc`)

They are exposed to your script via environment variables.

### Examples

```bash
supypowers examples run exponents:compute_sqrt "{'x': 9}"
supypowers examples run strings:reverse_string "{'s': 'abc'}"
supypowers examples run dates:add_days "{'d': '2025-01-01', 'days': 10}"
supypowers examples run exponents:compute_sqrt "{'x': 9}" --secrets .env --secrets API_KEY=abc
```

## Generating documentation

### JSON docs (for machines / LLM context)

```bash
supypowers <folder> docs --format json
supypowers <folder> docs --format json --output docs.json
```

The JSON output is a list of:

- `script`: path to the script
- `functions`: list of functions with `name`, `description`, `input_schema`, `output_schema`
- `error` (optional): if a script failed to load/inspect

### Markdown docs (for humans)

```bash
supypowers <folder> docs --format md
supypowers <folder> docs --format md --output docs.md
```

### Options

- `--recursive`: recurse into subfolders and include `**/*.py`
- `--require-marker`: only include functions explicitly marked (currently: decorator named `superpower`)

## Install `supypowers` on your PATH (so you can run `supypowers ...`)

If you don’t want to prefix every command with `uv run`, install the CLI as a uv “tool”:

Use `uv tool install`:

```bash
cd /Users/andre/ergodic/superpowers
uv tool install --editable .
uv tool update-shell
```

Then open a new shell (or reload your shell config) and run:

```bash
supypowers examples docs
supypowers examples run exponents:compute_sqrt \"{'x': 9}\"
```

## Example scripts

See `examples/` (uses `uv` script metadata + Pydantic models).

## Troubleshooting

- **`uv` not found**: install `uv` and ensure it’s on your `PATH`.
- **Docs command returns errors for a script**: run `uv run <script.py>` yourself to verify the script’s dependencies/imports are valid.
- **Input validation errors**: ensure you pass an object mapping with keys matching your input model fields.

## Notes (implementation)

- The CLI executes target scripts **only** via `uv run <script.py> ...` (no imports into the CLI process).
