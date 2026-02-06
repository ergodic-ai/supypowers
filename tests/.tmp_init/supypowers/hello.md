---
name: supypowers-authoring
description: How to create supypowers scripts. Use when you need to build a new Python function for the supypowers CLI.
---

# Creating Supypowers Scripts

Each supypowers script is a self-contained Python file in the `supypowers/` folder.
Scripts are run via `supypowers run <script>:<function> '<json>'` and always return JSON.

## Quick Start

```bash
supypowers new my_tool                                 # Create from template
supypowers run my_tool:my_tool '{"value": "test"}'   # Run it
supypowers skills                                      # See all functions
```

## Template

```python
# /// script
# dependencies = [
#   "pydantic",
# ]
# ///
from pydantic import BaseModel, Field


class MyInput(BaseModel):
    param1: str = Field(..., description="Description of param1")
    param2: int = Field(default=0, description="Optional with default")


class MyOutput(BaseModel):
    success: bool
    result: str | None = None
    error: str | None = None


def my_function(input: MyInput) -> MyOutput:
    """One-line description of what this function does."""
    try:
        return MyOutput(success=True, result=f"Got {input.param1}")
    except Exception as e:
        return MyOutput(success=False, error=str(e))
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
| 7 | Write a docstring — it becomes the function's description |
| 8 | Use `Field(..., description="...")` for all fields |

## Common Patterns

### HTTP requests

```python
# /// script
# dependencies = ["pydantic", "httpx"]
# ///
import httpx
from pydantic import BaseModel, Field

class FetchInput(BaseModel):
    url: str = Field(..., description="URL to fetch")

class FetchOutput(BaseModel):
    status: int
    body: str

def fetch_url(input: FetchInput) -> FetchOutput:
    """Fetch a URL and return its contents."""
    resp = httpx.get(input.url)
    return FetchOutput(status=resp.status_code, body=resp.text[:1000])
```

### Secrets

```bash
supypowers run my_script:my_func '{}' --secrets API_KEY=sk-xxx
supypowers run my_script:my_func '{}' --secrets .env
```

Access in code: `api_key = os.environ.get("API_KEY")`

### Optional fields

```python
class SearchInput(BaseModel):
    query: str = Field(..., description="Search query (required)")
    limit: int = Field(default=10, description="Max results")
```

### Error handling

```python
class ProcessOutput(BaseModel):
    success: bool
    result: str | None = None
    error: str | None = None

def process(input: ProcessInput) -> ProcessOutput:
    """Process something."""
    try:
        return ProcessOutput(success=True, result=do_work(input.data))
    except Exception as e:
        return ProcessOutput(success=False, error=str(e))
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `function not found` | Check spelling — case-sensitive |
| `input must be a Pydantic BaseModel` | Add type annotation: `def func(input: MyModel)` |
| `function must accept exactly one parameter` | Only one param named `input` allowed |
| Import error | Add the package to `# /// script` dependencies |
