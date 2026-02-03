from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from supypowers.uv_exec import UVRunError, uv_run_python_code
from supypowers.util import parse_secrets_args, resolve_script_path


SUPYPOWERS_FOLDER = "supypowers"


def app() -> None:
    parser = argparse.ArgumentParser(prog="supypowers")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="Initialize a supypowers/ folder with starter templates")
    init_p.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory (default: current directory). Creates supypowers/ inside it.",
    )
    init_p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing supypowers/hello.py and supypowers/hello.md if they exist.",
    )

    new_p = sub.add_parser("new", help="Create a new supypower script from template")
    new_p.add_argument("name", type=str, help="Name for the new script (without .py)")
    new_p.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory containing the supypowers/ folder (default: current directory).",
    )
    new_p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite if file already exists.",
    )

    run_p = sub.add_parser("run", help="Run a function in a script via `uv run`")
    run_p.add_argument("target", type=str, help="script:function (script may omit .py)")
    run_p.add_argument("input_data", type=str, help="Input data (JSON or Python-literal-ish)")
    run_p.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory containing the supypowers/ folder (default: current directory).",
    )
    run_p.add_argument(
        "--examples",
        action="store_true",
        help="Run from bundled examples instead of local supypowers/ folder.",
    )
    run_p.add_argument(
        "--secrets",
        action="append",
        default=[],
        help="Secrets as a .env path or inline KEY=VAL. May be provided multiple times.",
    )

    docs_p = sub.add_parser("docs", help="Emit docs JSON or Markdown for discovered functions")
    docs_p.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory containing the supypowers/ folder (default: current directory).",
    )
    docs_p.add_argument(
        "--examples",
        action="store_true",
        help="Document bundled examples instead of local supypowers/ folder.",
    )
    docs_p.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    docs_p.add_argument(
        "--format",
        choices=["json", "md"],
        default="json",
        help="Output format (json or md).",
    )
    docs_p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write output to a file instead of stdout.",
    )
    docs_p.add_argument(
        "--require-marker",
        action="store_true",
        help="Only include functions explicitly marked (currently: decorator named `superpower`).",
    )
    docs_p.add_argument(
        "--secrets",
        action="append",
        default=[],
        help="Secrets as a .env path or inline KEY=VAL. May be provided multiple times.",
    )

    skills_p = sub.add_parser(
        "skills", help="Generate a skills document for AI agents (what this is, available functions, how to use)"
    )
    skills_p.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory containing the supypowers/ folder (default: current directory).",
    )
    skills_p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write output to a file instead of stdout.",
    )
    skills_p.add_argument(
        "--secrets",
        action="append",
        default=[],
        help="Secrets as a .env path or inline KEY=VAL (needed if scripts require secrets to load).",
    )

    args = parser.parse_args()

    if args.command == "init":
        _cmd_init(args.root, force=bool(args.force))
        return
    if args.command == "new":
        _cmd_new(args.root, args.name, force=bool(args.force))
        return
    if args.command == "run":
        folder = _resolve_supypowers_folder(args.root, use_examples=args.examples)
        _cmd_run(folder, args.target, args.input_data, args.secrets)
        return
    if args.command == "docs":
        folder = _resolve_supypowers_folder(args.root, use_examples=args.examples)
        _cmd_docs(
            folder,
            args.recursive,
            args.require_marker,
            args.secrets,
            args.format,
            args.output,
        )
        return
    if args.command == "skills":
        folder = _resolve_supypowers_folder(args.root, use_examples=False)
        _cmd_skills(folder, args.secrets, args.output)
        return

    parser.error("unknown command")


def _resolve_supypowers_folder(root: Path, *, use_examples: bool) -> Path:
    """Resolve the supypowers folder, either from bundled examples or local."""
    if use_examples:
        # Use bundled examples directory (available when running from source)
        # The examples/ folder contains a supypowers/ subfolder following the convention
        examples_root = Path(__file__).parent.parent.parent / "examples"
        examples_dir = examples_root / SUPYPOWERS_FOLDER
        if not examples_dir.exists():
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "bundled examples not available (only in source install)",
                    }
                )
            )
            raise SystemExit(2)
        return examples_dir
    return (root / SUPYPOWERS_FOLDER).resolve()


def _cmd_init(root: Path, *, force: bool) -> None:
    if not root.exists() or not root.is_dir():
        print(json.dumps({"ok": False, "error": f"root directory not found: {root}"}))
        raise SystemExit(2)

    sp_dir = (root / SUPYPOWERS_FOLDER).resolve()
    sp_dir.mkdir(parents=True, exist_ok=True)

    hello_py = sp_dir / "hello.py"
    hello_md = sp_dir / "hello.md"

    if not force:
        for p in (hello_py, hello_md):
            if p.exists():
                print(
                    json.dumps(
                        {
                            "ok": False,
                            "error": f"refusing to overwrite existing file: {p}",
                            "hint": "re-run with --force to overwrite",
                        }
                    )
                )
                raise SystemExit(2)

    hello_py.write_text(_HELLO_PY, encoding="utf-8")
    hello_md.write_text(_HELLO_MD, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "created": [str(hello_py), str(hello_md)],
            }
        )
    )


def _cmd_new(root: Path, name: str, *, force: bool) -> None:
    sp_dir = (root / SUPYPOWERS_FOLDER).resolve()
    if not sp_dir.exists():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"supypowers/ folder not found at {sp_dir}",
                    "hint": "run 'supypowers init' first",
                }
            )
        )
        raise SystemExit(2)

    # Sanitize name
    script_name = name.replace("-", "_").replace(" ", "_")
    if not script_name.isidentifier():
        print(json.dumps({"ok": False, "error": f"invalid script name: {name}"}))
        raise SystemExit(2)

    script_path = sp_dir / f"{script_name}.py"
    if script_path.exists() and not force:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"file already exists: {script_path}",
                    "hint": "use --force to overwrite",
                }
            )
        )
        raise SystemExit(2)

    # Generate script content with the name
    content = _NEW_SCRIPT_TEMPLATE.format(
        script_name=script_name,
        class_name=_to_class_name(script_name),
    )
    script_path.write_text(content, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "created": str(script_path),
                "run_with": f"supypowers run {script_name}:{script_name} '{{\"value\": \"test\"}}'",
            }
        )
    )


def _to_class_name(snake_name: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in snake_name.split("_"))


def _cmd_run(folder: Path, target: str, input_data: str, secrets: list[str]) -> None:
    if not folder.exists() or not folder.is_dir():
        print(json.dumps({"ok": False, "error": f"folder not found: {folder}"}))
        raise SystemExit(2)

    script_name, _, func_name = target.partition(":")
    if not script_name or not func_name:
        print(json.dumps({"ok": False, "error": "target must be in the form script:function"}))
        raise SystemExit(2)

    script_path = resolve_script_path(folder, script_name)
    env = parse_secrets_args(secrets or [])

    payload = {
        "script_path": str(script_path),
        "function_name": func_name,
        "input_data": input_data,
    }

    try:
        out = uv_run_python_code(
            script_path=script_path,
            code=_RUNNER_CODE,
            payload=payload,
            extra_env=env,
        )
    except UVRunError as e:
        if e.stderr:
            sys.stderr.write(e.stderr + "\n")
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": e.message,
                    "exit_code": e.exit_code,
                    "uv_stdout": e.stdout,
                    "uv_stderr": e.stderr,
                }
            )
        )
        raise SystemExit(e.exit_code)

    try:
        parsed = json.loads(out)
    except Exception:
        print(json.dumps({"ok": False, "error": "runner did not emit valid JSON", "raw": out}))
        raise SystemExit(1)

    print(json.dumps(parsed, ensure_ascii=False))
    raise SystemExit(0 if parsed.get("ok") else 1)


def _cmd_docs(
    folder: Path,
    recursive: bool,
    require_marker: bool,
    secrets: list[str],
    out_format: str,
    output_path: Path | None,
) -> None:
    if not folder.exists() or not folder.is_dir():
        print(json.dumps({"ok": False, "error": f"folder not found: {folder}"}))
        raise SystemExit(2)

    env = parse_secrets_args(secrets or [])

    scripts = (
        sorted(p for p in folder.rglob("*.py") if p.is_file())
        if recursive
        else sorted(p for p in folder.glob("*.py") if p.is_file())
    )

    docs_out: list[dict] = []
    for script_path in scripts:
        payload = {"script_path": str(script_path), "require_marker": require_marker}
        try:
            out = uv_run_python_code(
                script_path=script_path,
                code=_DOCS_CODE,
                payload=payload,
                extra_env=env,
            )
            docs_out.append(json.loads(out))
        except Exception as e:
            docs_out.append({"script": str(script_path), "error": str(e), "functions": []})

    if out_format == "json":
        rendered = json.dumps(docs_out, ensure_ascii=False)
    else:
        rendered = _docs_to_markdown(docs_out)

    if output_path is not None:
        output_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


def _docs_to_markdown(docs_out: list[dict]) -> str:
    lines: list[str] = []
    lines.append("## Supypowers\n")
    for item in docs_out:
        script = item.get("script", "")
        err = item.get("error")
        lines.append(f"### `{script}`\n")
        if err:
            lines.append(f"**Error:** `{err}`\n")
            continue
        fns = item.get("functions") or []
        if not fns:
            lines.append("_No supypowers found._\n")
            continue
        for fn in fns:
            name = fn.get("name", "")
            desc = (fn.get("description") or "").strip()
            lines.append(f"#### `{name}`\n")
            if desc:
                lines.append(desc + "\n")
            in_schema = fn.get("input_schema")
            out_schema = fn.get("output_schema")
            lines.append("**Input schema**\n")
            lines.append("```json")
            lines.append(json.dumps(in_schema, ensure_ascii=False, indent=2))
            lines.append("```\n")
            lines.append("**Output schema**\n")
            lines.append("```json")
            lines.append(json.dumps(out_schema, ensure_ascii=False, indent=2))
            lines.append("```\n")
    return "\n".join(lines).rstrip() + "\n"


def _cmd_skills(folder: Path, secrets: list[str], output_path: Path | None) -> None:
    """Generate a comprehensive skills document for AI agents."""
    env = parse_secrets_args(secrets or [])

    # Gather function docs
    functions_info: list[dict] = []
    if folder.exists() and folder.is_dir():
        scripts = sorted(p for p in folder.glob("*.py") if p.is_file())
        for script_path in scripts:
            payload = {"script_path": str(script_path), "require_marker": False}
            try:
                out = uv_run_python_code(
                    script_path=script_path,
                    code=_DOCS_CODE,
                    payload=payload,
                    extra_env=env,
                )
                doc = json.loads(out)
                script_name = script_path.stem
                for fn in doc.get("functions", []):
                    functions_info.append(
                        {
                            "script": script_name,
                            "name": fn.get("name", ""),
                            "description": fn.get("description", ""),
                            "input_schema": fn.get("input_schema"),
                            "output_schema": fn.get("output_schema"),
                        }
                    )
            except Exception:
                pass  # Skip scripts that fail to load

    rendered = _generate_skills_markdown(functions_info)

    if output_path is not None:
        output_path.write_text(rendered, encoding="utf-8")
        print(json.dumps({"ok": True, "written_to": str(output_path)}))
    else:
        print(rendered)


def _generate_skills_markdown(functions: list[dict]) -> str:
    """Generate the skills markdown document."""
    lines: list[str] = []

    # Header
    lines.append("# Supypowers Skills")
    lines.append("")
    lines.append("This document describes the supypowers available to you and how to use them.")
    lines.append("")

    # What is supypowers
    lines.append("## What is Supypowers?")
    lines.append("")
    lines.append("Supypowers lets you run Python functions as tools. Each function:")
    lines.append("- Takes JSON input (validated via Pydantic)")
    lines.append("- Returns JSON output")
    lines.append("- Runs in isolation (dependencies are auto-installed)")
    lines.append("- Requires no environment setup")
    lines.append("")

    # Quick reference
    lines.append("## Quick Reference")
    lines.append("")
    lines.append("```bash")
    lines.append("# Run a function")
    lines.append("supypowers run <script>:<function> '<json_input>'")
    lines.append("")
    lines.append("# See all available functions")
    lines.append("supypowers docs --format json")
    lines.append("")
    lines.append("# Create a new script")
    lines.append("supypowers new <name>")
    lines.append("```")
    lines.append("")

    # Available functions
    lines.append("## Available Functions")
    lines.append("")

    if not functions:
        lines.append("_No functions available yet. Create one with `supypowers new <name>`._")
        lines.append("")
    else:
        for fn in functions:
            script = fn["script"]
            name = fn["name"]
            desc = fn.get("description", "").strip()
            in_schema = fn.get("input_schema")

            lines.append(f"### `{script}:{name}`")
            lines.append("")
            if desc:
                lines.append(desc)
                lines.append("")

            # Show how to run it
            lines.append("**Run:**")
            lines.append("```bash")
            # Generate example input from schema
            example_input = _schema_to_example_input(in_schema)
            lines.append(f"supypowers run {script}:{name} '{example_input}'")
            lines.append("```")
            lines.append("")

            # Show input schema
            if in_schema:
                props = in_schema.get("properties", {})
                required = set(in_schema.get("required", []))
                if props:
                    lines.append("**Input:**")
                    lines.append("| Field | Type | Required | Description |")
                    lines.append("|-------|------|----------|-------------|")
                    for field_name, field_info in props.items():
                        field_type = field_info.get("type", "any")
                        field_desc = field_info.get("description", "")
                        is_req = "yes" if field_name in required else "no"
                        lines.append(f"| `{field_name}` | {field_type} | {is_req} | {field_desc} |")
                    lines.append("")

    # How to create new functions
    lines.append("## Creating New Functions")
    lines.append("")
    lines.append("### 1. Create from template")
    lines.append("```bash")
    lines.append("supypowers new my_function")
    lines.append("```")
    lines.append("")
    lines.append("### 2. Edit the generated file")
    lines.append("Open `supypowers/my_function.py` and:")
    lines.append("- Update the Input model fields")
    lines.append("- Update the Output model fields")
    lines.append("- Implement your logic in the function body")
    lines.append("- Update the docstring")
    lines.append("")
    lines.append("### 3. Test it")
    lines.append("```bash")
    lines.append("supypowers run my_function:my_function '{\"value\": \"test\"}'")
    lines.append("```")
    lines.append("")

    # Rules
    lines.append("## Rules for Writing Functions")
    lines.append("")
    lines.append("1. Function must have exactly ONE parameter named `input`")
    lines.append("2. The `input` parameter must be typed as a Pydantic `BaseModel`")
    lines.append("3. Add dependencies to the `# /// script` block at the top")
    lines.append("4. Don't use `print()` - it breaks JSON output")
    lines.append("5. Don't use `input()` - there's no interactive terminal")
    lines.append("6. Return errors as part of output, don't raise exceptions")
    lines.append("")

    # Secrets
    lines.append("## Using Secrets")
    lines.append("")
    lines.append("Pass secrets via `--secrets`:")
    lines.append("```bash")
    lines.append("supypowers run my_script:my_func '{}' --secrets API_KEY=sk-xxx")
    lines.append("supypowers run my_script:my_func '{}' --secrets .env")
    lines.append("```")
    lines.append("")
    lines.append("Access in your script:")
    lines.append("```python")
    lines.append("import os")
    lines.append("api_key = os.environ.get('API_KEY')")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def _schema_to_example_input(schema: dict | None) -> str:
    """Generate an example JSON input from a schema."""
    if not schema:
        return "{}"

    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    example: dict = {}
    for field_name, field_info in props.items():
        if field_name not in required:
            continue  # Skip optional fields in example

        field_type = field_info.get("type", "string")
        if field_type == "string":
            example[field_name] = "..."
        elif field_type == "integer":
            example[field_name] = 0
        elif field_type == "number":
            example[field_name] = 0.0
        elif field_type == "boolean":
            example[field_name] = True
        elif field_type == "array":
            example[field_name] = []
        elif field_type == "object":
            example[field_name] = {}
        else:
            example[field_name] = "..."

    return json.dumps(example)


_RUNNER_CODE = r"""
import ast
import importlib.util
import inspect
import json
import sys
import typing

def _parse_input(s):
    s = s.strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    # "YAML-ish" best-effort: accept Python literals (e.g. {'x': 1}, [1,2], True, None).
    try:
        return ast.literal_eval(s)
    except Exception:
        raise ValueError("input_data must be valid JSON or a Python-literal-ish value")

def _load_module_from_path(path):
    spec = importlib.util.spec_from_file_location("__supypowers_target__", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _is_pydantic_model(cls):
    try:
        from pydantic import BaseModel
        return isinstance(cls, type) and issubclass(cls, BaseModel)
    except Exception:
        return False

def _resolved_type_hints(fn, mod):
    try:
        return typing.get_type_hints(fn, globalns=vars(mod), localns=vars(mod))
    except Exception:
        return {}

def _model_to_jsonable(obj):
    # Pydantic v2: model_dump(); v1: dict()
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj

def main():
    payload = json.loads(sys.stdin.read())
    script_path = payload["script_path"]
    fn_name = payload["function_name"]
    input_data = payload["input_data"]

    mod = _load_module_from_path(script_path)
    fn = getattr(mod, fn_name, None)
    if fn is None or not callable(fn):
        print(json.dumps({"ok": False, "error": f"function not found: {fn_name}"}))
        return 2

    sig = inspect.signature(fn)
    params = list(sig.parameters.values())
    if len(params) != 1:
        print(json.dumps({"ok": False, "error": "function must accept exactly one parameter named `input`"}))
        return 2

    param = params[0]
    if param.name != "input":
        print(json.dumps({"ok": False, "error": "function parameter must be named `input`"}))
        return 2

    hints = _resolved_type_hints(fn, mod)
    ann = hints.get(param.name, param.annotation)
    raw = _parse_input(input_data)

    try:
        if not _is_pydantic_model(ann):
            print(json.dumps({"ok": False, "error": "input must be a Pydantic BaseModel type annotation"}))
            return 2
        if not isinstance(raw, dict):
            print(json.dumps({"ok": False, "error": "input_data must be an object mapping for the input model"}))
            return 2
        inp = ann.model_validate(raw) if hasattr(ann, "model_validate") else ann.parse_obj(raw)
        result = fn(inp)
        out = _model_to_jsonable(result)
        try:
            json.dumps(out)
        except Exception:
            out = str(out)
        print(json.dumps({"ok": True, "data": out}, ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""


_DOCS_CODE = r"""
import ast
import importlib.util
import inspect
import json
import sys
import typing

def _load_module_from_path(path):
    spec = importlib.util.spec_from_file_location("__supypowers_target__", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _is_pydantic_model(cls):
    try:
        from pydantic import BaseModel
        return isinstance(cls, type) and issubclass(cls, BaseModel)
    except Exception:
        return False

def _resolved_type_hints(fn, mod):
    try:
        return typing.get_type_hints(fn, globalns=vars(mod), localns=vars(mod))
    except Exception:
        return {}

def _schema_for_model(model_cls):
    try:
        return model_cls.model_json_schema()
    except Exception:
        try:
            return model_cls.schema()
        except Exception:
            return None

def _has_superpower_decorator(script_path, fn_name):
    try:
        src = open(script_path, "r", encoding="utf-8").read()
        tree = ast.parse(src)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Name) and dec.id == "superpower":
                        return True
                    if isinstance(dec, ast.Attribute) and dec.attr == "superpower":
                        return True
        return False
    except Exception:
        return False

def main():
    payload = json.loads(sys.stdin.read())
    script_path = payload["script_path"]
    require_marker = bool(payload.get("require_marker"))

    mod = _load_module_from_path(script_path)

    fns = []
    for name, obj in sorted(vars(mod).items()):
        if name.startswith("_"):
            continue
        if not callable(obj):
            continue
        try:
            sig = inspect.signature(obj)
        except Exception:
            continue
        params = list(sig.parameters.values())
        if len(params) != 1:
            continue
        if params[0].name != "input":
            continue
        hints = _resolved_type_hints(obj, mod)
        ann_in = hints.get(params[0].name, params[0].annotation)
        if require_marker and not _has_superpower_decorator(script_path, name):
            continue
        if not _is_pydantic_model(ann_in):
            continue

        ann_out = hints.get("return", sig.return_annotation)
        fns.append({
            "name": name,
            "description": inspect.getdoc(obj) or "",
            "input_schema": _schema_for_model(ann_in) if _is_pydantic_model(ann_in) else None,
            "output_schema": _schema_for_model(ann_out) if _is_pydantic_model(ann_out) else None,
        })

    print(json.dumps({"script": script_path, "functions": fns}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""


_HELLO_PY = """# /// script
# dependencies = [
#   "pydantic",
# ]
# ///
\"\"\"
hello.py - Example supypower script

Run with:   supypowers run hello:hello "{'name': 'World'}"
\"\"\"
from pydantic import BaseModel, Field


# ============================================================================
# STEP 1: Define your INPUT model (required)
# ============================================================================
class HelloInput(BaseModel):
    name: str = Field(..., description="Name to greet.")


# ============================================================================
# STEP 2: Define your OUTPUT model (recommended but optional)
# ============================================================================
class HelloOutput(BaseModel):
    greeting: str = Field(..., description="A friendly greeting.")


# ============================================================================
# STEP 3: Write your function
# - Must have exactly ONE parameter named `input`
# - `input` must be typed as a Pydantic BaseModel
# - Add a docstring (it becomes the function's description)
# ============================================================================
def hello(input: HelloInput) -> HelloOutput:
    \"\"\"Generate a friendly greeting for the given name.\"\"\"
    return HelloOutput(greeting=f"Hello, {input.name}!")
"""


_HELLO_MD = """# How to Build Supypowers (for AI Agents)

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
    \"\"\"One-line description of what this function does.\"\"\"
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
    \"\"\"Fetch a URL and return its contents.\"\"\"
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
    \"\"\"Process something, returning success/error status.\"\"\"
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
"""


_NEW_SCRIPT_TEMPLATE = """# /// script
# dependencies = [
#   "pydantic",
# ]
# ///
\"\"\"
{script_name}.py - TODO: describe what this script does

Run with: supypowers run {script_name}:{script_name} '{{"value": "test"}}'
\"\"\"
from typing import Optional
from pydantic import BaseModel, Field


class {class_name}Input(BaseModel):
    \"\"\"Input for {script_name}.\"\"\"
    value: str = Field(..., description="TODO: describe this field")
    # Add more fields as needed:
    # count: int = Field(default=10, description="Optional field with default")


class {class_name}Output(BaseModel):
    \"\"\"Output for {script_name}.\"\"\"
    success: bool = Field(..., description="Whether the operation succeeded")
    result: Optional[str] = Field(default=None, description="The result if successful")
    error: Optional[str] = Field(default=None, description="Error message if failed")


def {script_name}(input: {class_name}Input) -> {class_name}Output:
    \"\"\"TODO: describe what this function does.\"\"\"
    try:
        # TODO: implement your logic here
        result = f"Processed: {{input.value}}"
        return {class_name}Output(success=True, result=result)
    except Exception as e:
        return {class_name}Output(success=False, error=str(e))
"""


if __name__ == "__main__":
    app()

