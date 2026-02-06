# Supypowers — Skills Guide

Supypowers scripts are modular capabilities that extend an AI agent's functionality. Each script packages a Python function with typed inputs/outputs and auto-managed dependencies, so agents can run them as tools without any setup.

## How Supypowers Maps to Agent Skills

[Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) are reusable, filesystem-based resources that give AI agents domain-specific expertise. Supypowers follows the same philosophy:

| Agent Skills Concept | Supypowers Equivalent |
|---|---|
| `SKILL.md` (instructions) | `supypowers skills` output |
| Skill metadata (name, description) | YAML frontmatter in skills output |
| Bundled scripts | `supypowers/*.py` files |
| Skill resources | Input/output schemas, docstrings |
| Progressive loading | `supypowers docs --format json` for on-demand schema lookup |

## Generating a SKILL.md

The `skills` command emits a ready-to-use `SKILL.md` with YAML frontmatter:

```bash
supypowers skills --output SKILL.md
```

The output follows the Agent Skills format:

```yaml
---
name: supypowers
description: Run Python functions as tools via the supypowers CLI. Use when you need to call any of the available functions listed below.
---

# Supypowers

## Quick Start
...

## Available Functions
...
```

This means you can drop the output directly into `.claude/skills/` (for Claude Code), upload it via the Skills API, or include it as agent context.

## Three Levels of Information

Following the Agent Skills progressive-disclosure model, supypowers provides information at three levels:

### Level 1: Metadata (lightweight)

The YAML frontmatter in `SKILL.md` tells the agent what supypowers is and when to use it. This is all that needs to be loaded at startup — just a name and description.

### Level 2: Instructions (loaded when triggered)

The body of `SKILL.md` contains:
- Quick-start commands
- A table of all available functions with descriptions and example invocations
- Input field details (type, required, description)
- Rules for creating new functions

### Level 3: Schemas & Code (loaded as needed)

For deeper inspection, the agent can run:
```bash
supypowers docs --format json    # Full JSON schemas for all functions
```

This returns complete input/output schemas without consuming context upfront.

## Using Supypowers as Agent Skills

### In Claude Code

Place the generated `SKILL.md` in your project:

```bash
mkdir -p .claude/skills/supypowers
supypowers skills --output .claude/skills/supypowers/SKILL.md
```

Claude Code will discover and use it automatically.

### In the Claude API

Upload the `SKILL.md` as a custom Skill via the `/v1/skills` endpoint, or include the skills output in your system prompt.

### In Cursor / Other Agents

Use the skills output as a rules file or agent context:

```bash
supypowers skills --output AGENTS.md
```

Or include it in `.cursorrules`, `.cursor/rules/`, or any agent configuration that accepts markdown instructions.

## Generating Docs in SKILL.md Format

### Skills document (recommended for agents)

```bash
supypowers skills                    # Print to stdout
supypowers skills --output SKILL.md  # Write to file
```

Produces a complete `SKILL.md` with:
- YAML frontmatter (`name`, `description`)
- Quick-start instructions
- All available functions with schemas and examples
- Rules for creating new functions
- Secrets usage guide

### Markdown docs (reference format)

```bash
supypowers docs --format md                # Print to stdout
supypowers docs --format md --output docs.md  # Write to file
```

Produces a reference document listing every function with full input/output JSON schemas.

### JSON docs (for programmatic use)

```bash
supypowers docs --format json
```

Returns the raw function metadata for programmatic consumption.

## Writing Scripts That Work as Skills

Each supypowers script is a self-contained Python file. To maximize usefulness as an agent skill:

1. **Write clear docstrings** — The docstring becomes the function's description in the skills document
2. **Use descriptive Field annotations** — `Field(..., description="...")` feeds into the input table
3. **Name things well** — Script and function names appear in the `run` command
4. **Handle errors in output** — Use `success: bool` + `error: str | None` pattern
5. **Declare all dependencies** — The `# /// script` block must list everything you import

### Example: A Well-Documented Script

```python
# /// script
# dependencies = ["pydantic", "httpx"]
# ///
"""
weather.py — Fetch current weather for a location.

Run with: supypowers run weather:get_weather '{"city": "London"}'
"""
from pydantic import BaseModel, Field
import httpx


class GetWeatherInput(BaseModel):
    city: str = Field(..., description="City name to get weather for")
    units: str = Field(default="metric", description="Temperature units: metric or imperial")


class GetWeatherOutput(BaseModel):
    success: bool
    temperature: float | None = None
    description: str | None = None
    error: str | None = None


def get_weather(input: GetWeatherInput) -> GetWeatherOutput:
    """Fetch current weather conditions for a city."""
    try:
        resp = httpx.get(f"https://wttr.in/{input.city}?format=j1")
        data = resp.json()
        current = data["current_condition"][0]
        temp_key = "temp_C" if input.units == "metric" else "temp_F"
        return GetWeatherOutput(
            success=True,
            temperature=float(current[temp_key]),
            description=current["weatherDesc"][0]["value"],
        )
    except Exception as e:
        return GetWeatherOutput(success=False, error=str(e))
```

This script will appear in `supypowers skills` output as:

```
### `weather:get_weather`

Fetch current weather conditions for a city.

**Run:**
supypowers run weather:get_weather '{"city": "..."}'

**Input:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `city` | string | yes | City name to get weather for |
| `units` | string | no | Temperature units: metric or imperial |
```

## File Structure

```
project/
├── supypowers/              # All scripts go here
│   ├── hello.py             # Starter example
│   ├── weather.py           # Your custom scripts
│   └── ...
├── SKILL.md                 # Generated: supypowers skills --output SKILL.md
└── .claude/skills/          # Optional: for Claude Code auto-discovery
    └── supypowers/
        └── SKILL.md
```
