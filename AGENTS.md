---
name: supypowers
description: Run Python functions as tools without managing environments or dependencies. Use when you need to execute a supypower function, create a new one, or inspect available capabilities.
---

# Supypowers — Agent Guide

You can run Python functions as tools without managing environments or dependencies.

## Quick Start

```bash
supypowers skills              # See all available functions + how to use them
supypowers run <script>:<func> '<json>'   # Run a function
supypowers new <name>          # Create a new function
```

> **If `supypowers` command not found:** Use `uvx supypowers ...` or `uv run supypowers ...` instead.

## Install

Choose one method:

```bash
# Option 1: Global CLI (recommended)
uv tool install supypowers

# Option 2: No install needed (run via uvx)
uvx supypowers skills

# Option 3: Add to project, run with uv run
uv add supypowers
uv run supypowers skills
```

After `uv tool install`, you can use `supypowers` directly. Otherwise, prefix commands with `uvx` or `uv run`.

## Step 1: See What's Available

```bash
supypowers skills
```

This shows you:
- All available functions with descriptions
- Input field tables (type, required, description)
- Example commands to run each function

For full JSON schemas (programmatic use):
```bash
supypowers docs --format json
```

## Step 2: Run a Function

```bash
supypowers run <script>:<function> '<json_input>'
```

**Examples:**
```bash
supypowers run hello:hello '{"name": "World"}'
supypowers run math:calculate '{"x": 10, "y": 5}'
```

**Output:** Always JSON — `{"ok": true, "data": ...}` or `{"ok": false, "error": "..."}`

**With secrets:**
```bash
supypowers run my_api:fetch '{"query": "test"}' --secrets API_KEY=sk-xxx
supypowers run my_api:fetch '{"query": "test"}' --secrets .env
```

## Step 3: Create New Functions

When you need a capability that doesn't exist:

```bash
supypowers new my_tool
```

This creates `powers/my_tool.py` with a ready-to-edit template.

### Edit the file

```python
# /// script
# dependencies = [
#   "pydantic",
# ]
# ///
from pydantic import BaseModel, Field

class MyToolInput(BaseModel):
    value: str = Field(..., description="TODO: describe this field")

class MyToolOutput(BaseModel):
    success: bool
    result: str | None = None
    error: str | None = None

def my_tool(input: MyToolInput) -> MyToolOutput:
    """TODO: describe what this function does."""
    try:
        return MyToolOutput(success=True, result=f"Got: {input.value}")
    except Exception as e:
        return MyToolOutput(success=False, error=str(e))
```

### What to modify:
1. **Input fields** — Change `value` to the fields you need
2. **Output fields** — Change to match what you return
3. **Dependencies** — Add any packages you need (e.g., `"httpx"`, `"beautifulsoup4"`)
4. **Docstring** — Describe what the function does
5. **Logic** — Implement the actual functionality

### Test it
```bash
supypowers run my_tool:my_tool '{"value": "test"}'
```

## Rules

| # | Rule |
|---|------|
| 1 | Function must have exactly **one** parameter named `input` |
| 2 | `input` must be typed as a Pydantic `BaseModel` |
| 3 | Declare all dependencies in the `# /// script` block |
| 4 | **No `print()`** — it breaks JSON output |
| 5 | **No `input()`** — there is no interactive terminal |
| 6 | Return errors in output; don't raise exceptions |

## Common Patterns

### HTTP requests
```python
# /// script
# dependencies = ["pydantic", "httpx"]
# ///
import httpx

def fetch(input: FetchInput) -> FetchOutput:
    resp = httpx.get(input.url)
    return FetchOutput(status=resp.status_code, body=resp.text)
```

### Using secrets
```python
import os

def call_api(input: ApiInput) -> ApiOutput:
    api_key = os.environ.get("API_KEY")
    # Use api_key in your request
```

### Optional fields
```python
class SearchInput(BaseModel):
    query: str = Field(..., description="Required search query")
    limit: int = Field(default=10, description="Optional, defaults to 10")
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `function not found` | Check spelling — case-sensitive |
| `input must be a Pydantic BaseModel` | Add type annotation: `def func(input: MyModel)` |
| `function must accept exactly one parameter` | Only one param named `input` allowed |
| Import error | Add the package to `# /// script` dependencies |

## File Structure

```
project/
├── powers/              # All scripts go here
│   ├── hello.py
│   ├── my_tool.py
│   └── hello.md         # Guide for writing scripts (optional reading)
└── ...
```

## Summary

```bash
supypowers skills                    # What can I do?
supypowers run script:func '{...}'   # Do it
supypowers new name                  # Make something new
```
