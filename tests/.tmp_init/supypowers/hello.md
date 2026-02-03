# How to Build Supypowers (for AI Agents)

This guide explains how to create Python scripts that work with the `supypowers` CLI.

## Quick Reference

```
Location:    supypowers/<script_name>.py
Run:         supypowers run <script>:<function> '<json_input>'
Docs:        supypowers docs --format json
```

## Checklist (follow this exactly)

- [ ] File starts with `# /// script` dependency block
- [ ] Has `"pydantic"` in dependencies (plus any others you need)
- [ ] Defines a Pydantic `BaseModel` for input
- [ ] Function has exactly ONE parameter named `input`
- [ ] Parameter `input` is typed as your Pydantic model
- [ ] Function has a docstring (becomes the description)

## Template (copy this)

```python
# /// script
# dependencies = [
#   "pydantic",
# ]
# ///
from pydantic import BaseModel, Field


class MyInput(BaseModel):
    # Define your input fields here
    param1: str = Field(..., description="Description of param1")
    param2: int = Field(default=0, description="Optional param with default")


class MyOutput(BaseModel):
    result: str = Field(..., description="The result")


def my_function(input: MyInput) -> MyOutput:
    """One-line description of what this function does."""
    # Your logic here
    return MyOutput(result=f"Got {input.param1}")
```

## Common Patterns

### Using environment variables (secrets)

Pass secrets via `--secrets`:
```bash
supypowers run my_script:my_func '{}' --secrets API_KEY=sk-xxx
supypowers run my_script:my_func '{}' --secrets .env
```

Access in your script:
```python
import os
api_key = os.environ.get("API_KEY")
```

### Making HTTP requests

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

### Optional fields with defaults

```python
class SearchInput(BaseModel):
    query: str = Field(..., description="Search query (required)")
    limit: int = Field(default=10, description="Max results (optional, default 10)")
    include_metadata: bool = Field(default=False, description="Include metadata?")
```

### Lists and nested objects

```python
from typing import List, Optional

class Item(BaseModel):
    name: str
    value: float

class BatchInput(BaseModel):
    items: List[Item] = Field(..., description="List of items to process")
    tag: Optional[str] = Field(default=None, description="Optional tag")
```

### Returning errors gracefully

Return errors as part of your output model (don't raise exceptions):

```python
class ProcessOutput(BaseModel):
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None


def process(input: ProcessInput) -> ProcessOutput:
    """Process something, returning success/error status."""
    try:
        result = do_something(input.data)
        return ProcessOutput(success=True, result=result)
    except Exception as e:
        return ProcessOutput(success=False, error=str(e))
```

## DO and DON'T

### DO
- Use descriptive `Field(..., description="...")` for all fields
- Write clear docstrings (they become function descriptions)
- Return Pydantic models for structured output
- Handle errors gracefully within your function
- Use `httpx` for HTTP requests (it's cleaner than `requests`)

### DON'T
- Don't name the parameter anything other than `input`
- Don't use multiple parameters (only one `input` param allowed)
- Don't print() to stdout (it breaks JSON output)
- Don't use input() or any interactive prompts
- Don't forget to add dependencies to the `# /// script` block

## Running and Testing

```bash
# Run a function
supypowers run hello:hello "{'name': 'World'}"

# See all available functions
supypowers docs --format json

# Human-readable docs
supypowers docs --format md
```

## Troubleshooting

**"function not found"** - Check that function name matches exactly (case-sensitive)

**"input must be a Pydantic BaseModel"** - Your input parameter isn't typed as a BaseModel

**"function must accept exactly one parameter"** - You have 0 or 2+ parameters

**Dependency not found** - Add it to the `# /// script` dependencies block
