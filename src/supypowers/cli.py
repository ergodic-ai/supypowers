from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from supypowers.uv_exec import UVRunError, uv_run_python_code
from supypowers.util import parse_secrets_args, resolve_script_path


def app() -> None:
    parser = argparse.ArgumentParser(prog="supypowers")
    parser.add_argument("folder", type=Path, help="Folder containing scripts")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="Initialize a supypowers folder with starter templates")
    init_p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing supypowers/hello.py and supypowers/hello.md if they exist.",
    )

    run_p = sub.add_parser("run", help="Run a function in a script via `uv run`")
    run_p.add_argument("target", type=str, help="script:function (script may omit .py)")
    run_p.add_argument("input_data", type=str, help="Input data (JSON or Python-literal-ish)")
    run_p.add_argument(
        "--secrets",
        action="append",
        default=[],
        help="Secrets as a .env path or inline KEY=VAL. May be provided multiple times.",
    )

    docs_p = sub.add_parser("docs", help="Emit docs JSON or Markdown for discovered functions")
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

    args = parser.parse_args()

    if args.command == "init":
        _cmd_init(args.folder, force=bool(args.force))
        return
    if args.command == "run":
        _cmd_run(args.folder, args.target, args.input_data, args.secrets)
        return
    if args.command == "docs":
        _cmd_docs(
            args.folder,
            args.recursive,
            args.require_marker,
            args.secrets,
            args.format,
            args.output,
        )
        return

    parser.error("unknown command")


def _cmd_init(folder: Path, *, force: bool) -> None:
    if not folder.exists() or not folder.is_dir():
        print(json.dumps({"ok": False, "error": f"folder not found: {folder}"}))
        raise SystemExit(2)

    sp_dir = (folder / "supypowers").resolve()
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

\"\"\"hello.py - a starter supypower script

This file is meant to be copied and edited.
\"\"\"

from __future__ import annotations

from pydantic import BaseModel, Field


class HelloInput(BaseModel):
    name: str = Field(..., description="Name to greet.")


class HelloOutput(BaseModel):
    greeting: str = Field(..., description="A friendly greeting.")


def hello(input: HelloInput) -> HelloOutput:
    \"\"\"Say hello.\"\"\"
    return HelloOutput(greeting=f"Hello, {input.name}!")
"""


_HELLO_MD = """## Building a supypower script (for AI agents)

Your job: create a Python script that defines one or more *supypower* functions.

### 1) Add uv inline dependencies

At the very top of the file, include:

```text
# /// script
# dependencies = [
#   "pydantic",
# ]
# ///
```

This allows the script to run in isolation without a virtualenv.

### 2) Define a Pydantic input model

Each supypower function must accept exactly one parameter named `input`.
The type of `input` must be a Pydantic `BaseModel`.

### 3) (Optional) Define a Pydantic output model

Returning a Pydantic model is recommended because it produces clean JSON output.
You can return any type, but JSON-serializable types are best.

### 4) Write the function

Contract:
- The function has exactly **one** parameter named **`input`**
- `input` is annotated as a **Pydantic BaseModel**
- Add a clear docstring (used for documentation)

Example:

```python
def hello(input: HelloInput) -> HelloOutput:
    \"\"\"Say hello.\"\"\"
    return HelloOutput(greeting=f\"Hello, {input.name}!\")
```

### 5) Run it

From a folder that contains your script (e.g. `.`):

```bash
supypowers . run hello:hello \"{'name': 'World'}\"
```

### 6) Generate documentation

```bash
supypowers . docs --format json --output docs.json
supypowers . docs --format md --output docs.md
```
"""


if __name__ == "__main__":
    app()

