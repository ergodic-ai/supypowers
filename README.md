# supypowers

Run self-contained Python scripts (with `uv` script dependencies) as callable, schema-documented functions.

**Designed for AI agents**: Create, discover, and execute typed Python functions without managing environments.

## What you can do with this

- **Run** a typed function in a script: validate/coerce JSON input with Pydantic, execute, emit JSON output.
- **Generate documentation** for all scripts in a folder as either **JSON** (for machines/LLMs) or **Markdown** (for humans).
- **Scaffold new scripts** instantly with `supypowers new <name>`

## For AI Agents

**👉 See [AGENTS.md](AGENTS.md) for the complete agent guide.**

Quick start:
```bash
supypowers skills                    # What can I do?
supypowers run script:func '{...}'   # Do it
supypowers new name                  # Make something new
```

All scripts live in the `supypowers/` folder. All output is JSON.

## Prerequisites

- **`uv`** must be installed and on your `PATH` (the CLI shells out to `uv run`).

## Install

### Using uv (recommended)

```bash
# Install as a global CLI tool
uv tool install supypowers

# Or run without installing (ephemeral)
uvx supypowers skills
```

### Using pip

```bash
pip install supypowers
```

> **Note:** `uv add supypowers` adds it as a project dependency but won't expose the CLI globally. Use `uv tool install` for a global command, or `uv run supypowers` within your project.

## Quickstart

```bash
# 1. Initialize a new supypowers/ folder
supypowers init

# 2. Create a new script from template
supypowers new my_tool

# 3. Edit supypowers/my_tool.py to implement your logic

# 4. Run it
supypowers run my_tool:my_tool '{"value": "test"}'

# 5. See all available functions
supypowers docs --format json
```

The `init` command creates `supypowers/hello.py` (example) and `supypowers/hello.md` (instructions for agents).

Try the bundled examples (when running from source):

```bash
supypowers run --examples exponents:compute_sqrt "{'x': 9}"
supypowers docs --examples --format md
```

## Core concepts

### Folder convention

All scripts live in a `supypowers/` folder in your project root. This is hardcoded by convention to keep the CLI simple for agents.

```
my-project/
├── supypowers/
│   ├── hello.py
│   └── math.py
└── ...
```

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

A function is considered a "supypower" if it matches this contract:

- **Exactly one parameter**, named **`input`**
- The `input` type is a **Pydantic `BaseModel`**
- Input data is **validated/coerced** via Pydantic (it must be an object mapping)
- Output can be any type; if it's a Pydantic model, it will be emitted in JSON-friendly form

See `examples/exponents.py` in the source repo for the canonical pattern.

## Creating new scripts

### Syntax

```bash
supypowers new <name>
```

Creates a new script `supypowers/<name>.py` from a template with:
- Dependency block already set up
- Input/Output Pydantic models
- Error handling pattern
- TODO comments showing where to customize

### Example

```bash
supypowers new fetch_weather
# Creates supypowers/fetch_weather.py
# Edit the file, then run:
supypowers run fetch_weather:fetch_weather '{"city": "London"}'
```

## Running functions

### Syntax

```bash
supypowers run <script>:<function> <input_data> [--secrets ...]
```

The CLI looks for scripts in the `supypowers/` folder of the current directory.

### Input format (`<input_data>`)

- **Preferred**: strict JSON (e.g. `{"x": 9}`)
- **Also supported** ("YAML-ish"): Python literal objects (e.g. `{'x': 9}`) via `ast.literal_eval`

Supypowers will then validate/coerce that object into your Pydantic model.

### Secrets (`--secrets`)

You can pass secrets as:

- a **dotenv file path** (e.g. `--secrets .env`)
- **inline** `KEY=VAL` pairs (e.g. `--secrets API_KEY=abc`)

They are exposed to your script via environment variables.

### Options

- `--root <path>`: Use a different root directory (default: current directory)
- `--examples`: Run from bundled examples instead of local `supypowers/` folder

### Examples

```bash
supypowers run hello:hello "{'name': 'World'}"
supypowers run math:compute_sqrt "{'x': 9}"
supypowers run math:compute_sqrt "{'x': 9}" --secrets .env --secrets API_KEY=abc

# Run from bundled examples (source install only)
supypowers run --examples exponents:compute_sqrt "{'x': 9}"
supypowers run --examples strings:reverse_string "{'s': 'abc'}"
supypowers run --examples dates:add_days "{'d': '2025-01-01', 'days': 10}"
```

## Generating documentation

### JSON docs (for machines / LLM context)

```bash
supypowers docs --format json
supypowers docs --format json --output docs.json
```

The JSON output is a list of:

- `script`: path to the script
- `functions`: list of functions with `name`, `description`, `input_schema`, `output_schema`
- `error` (optional): if a script failed to load/inspect

### Markdown docs (for humans)

```bash
supypowers docs --format md
supypowers docs --format md --output docs.md
```

### Options

- `--root <path>`: Use a different root directory (default: current directory)
- `--examples`: Document bundled examples instead of local `supypowers/` folder
- `--recursive`: recurse into subfolders and include `**/*.py`
- `--require-marker`: only include functions explicitly marked (currently: decorator named `superpower`)

## Generating skills document (for AI agents)

The `skills` command generates a comprehensive markdown document that teaches an AI agent everything it needs to know:

```bash
supypowers skills
supypowers skills --output SKILLS.md
```

The output includes:
- What supypowers is and how it works
- All available functions with their input schemas
- Example commands to run each function
- How to create new functions
- Rules and best practices
- How to use secrets

This is the recommended way to give an AI agent context about your supypowers.

## Install `supypowers` on your PATH (so you can run `supypowers ...`)

If you don't want to prefix every command with `uv run`, install the CLI as a uv "tool":

Use `uv tool install`:

```bash
uv tool install supypowers
uv tool update-shell
```

Then open a new shell (or reload your shell config) and run:

```bash
supypowers init
supypowers run hello:hello "{'name': 'World'}"
```

## Example scripts

See `examples/` (uses `uv` script metadata + Pydantic models).

## Troubleshooting

- **`uv` not found**: install `uv` and ensure it’s on your `PATH`.
- **Docs command returns errors for a script**: run `uv run <script.py>` yourself to verify the script’s dependencies/imports are valid.
- **Input validation errors**: ensure you pass an object mapping with keys matching your input model fields.

## Notes (implementation)

- The CLI executes target scripts **only** via `uv run <script.py> ...` (no imports into the CLI process).
