from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from supypowers.uv_exec import UVRunError, uv_run_python_code
from supypowers.util import parse_secrets_args, resolve_script_path


POWERS_FOLDER = "powers"
_LEGACY_FOLDER = "supypowers"


def app() -> None:
    parser = argparse.ArgumentParser(prog="supypowers")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="Initialize a powers/ folder with starter templates")
    init_p.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory (default: current directory). Creates powers/ inside it.",
    )
    init_p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing powers/hello.py and powers/hello.md if they exist.",
    )

    new_p = sub.add_parser("new", help="Create a new supypower script from template")
    new_p.add_argument("name", type=str, help="Name for the new script (without .py)")
    new_p.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory containing the powers/ folder (default: current directory).",
    )
    new_p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite if file already exists.",
    )

    run_p = sub.add_parser("run", help="Run a function in a script via `uv run`")
    run_p.add_argument("target", type=str, help="script:function (script may omit .py)")
    run_p.add_argument("input_data", type=str, nargs="?", default="{}", help="Input data (JSON or Python-literal-ish). Optional for no-input functions.")
    run_p.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory containing the powers/ folder (default: current directory).",
    )
    run_p.add_argument(
        "--examples",
        action="store_true",
        help="Run from bundled examples instead of local powers/ folder.",
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
        help="Root directory containing the powers/ folder (default: current directory).",
    )
    docs_p.add_argument(
        "--examples",
        action="store_true",
        help="Document bundled examples instead of local powers/ folder.",
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

    test_p = sub.add_parser("test", help="Test a function with auto-generated example input or a fixture file")
    test_p.add_argument("target", type=str, help="script:function to test")
    test_p.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory containing the powers/ folder (default: current directory).",
    )
    test_p.add_argument(
        "--examples",
        action="store_true",
        help="Test from bundled examples instead of local powers/ folder.",
    )
    test_p.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Path to a JSON file containing test input.",
    )
    test_p.add_argument(
        "--secrets",
        action="append",
        default=[],
        help="Secrets as a .env path or inline KEY=VAL.",
    )

    skills_p = sub.add_parser(
        "skills", help="Generate skill files for AI agents (one per script in powers/)"
    )
    skills_p.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root directory containing the powers/ folder (default: current directory).",
    )
    skills_p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for skill files (default: .claude/skills/).",
    )
    skills_p.add_argument(
        "--stdout",
        action="store_true",
        help="Print all skill content to stdout instead of writing files.",
    )
    skills_p.add_argument(
        "--all",
        dest="select_all",
        action="store_true",
        help="Write skills to all detected AI tool folders without prompting.",
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
        folder = _resolve_powers_folder(args.root, use_examples=args.examples)
        _cmd_run(folder, args.target, args.input_data, args.secrets)
        return
    if args.command == "test":
        folder = _resolve_powers_folder(args.root, use_examples=args.examples)
        _cmd_test(folder, args.target, args.fixture, args.secrets)
        return
    if args.command == "docs":
        folder = _resolve_powers_folder(args.root, use_examples=args.examples)
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
        folder = _resolve_powers_folder(args.root, use_examples=False)
        _cmd_skills(folder, args.secrets, args.output, args.stdout, args.select_all, args.root)
        return

    parser.error("unknown command")


def _resolve_powers_folder(root: Path, *, use_examples: bool) -> Path:
    """Resolve the powers folder, either from bundled examples or local."""
    if use_examples:
        # Use bundled examples directory (available when running from source)
        examples_root = Path(__file__).parent.parent.parent / "examples"
        examples_dir = examples_root / POWERS_FOLDER
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
    powers_dir = (root / POWERS_FOLDER).resolve()
    if powers_dir.exists():
        return powers_dir
    # Fallback to legacy folder name
    legacy_dir = (root / _LEGACY_FOLDER).resolve()
    if legacy_dir.exists():
        print(f"Warning: '{_LEGACY_FOLDER}/' is deprecated, rename to '{POWERS_FOLDER}/'", file=sys.stderr)
        return legacy_dir
    return powers_dir  # return expected path (will fail later with clear error)


def _cmd_init(root: Path, *, force: bool) -> None:
    if not root.exists() or not root.is_dir():
        print(json.dumps({"ok": False, "error": f"root directory not found: {root}"}))
        raise SystemExit(2)

    sp_dir = (root / POWERS_FOLDER).resolve()
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
    sp_dir = _resolve_powers_folder(root, use_examples=False)
    if not sp_dir.exists():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"powers/ folder not found at {sp_dir}",
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

    try:
        script_path = resolve_script_path(folder, script_name)
    except FileNotFoundError as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        raise SystemExit(2)
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
    except json.JSONDecodeError:
        # Defense in depth: try the last JSON-like line in case of stray stdout
        # output that wasn't caught by the runner's stdout→stderr redirect
        # (e.g. C extensions writing directly to fd 1).
        parsed = None
        for line in reversed(out.strip().splitlines()):
            try:
                parsed = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
        if parsed is None:
            print(json.dumps({"ok": False, "error": "runner did not emit valid JSON", "raw": out}))
            raise SystemExit(1)

    print(json.dumps(parsed, ensure_ascii=False))
    raise SystemExit(0 if parsed.get("ok") else 1)


def _cmd_test(folder: Path, target: str, fixture: Path | None, secrets: list[str]) -> None:
    """Test a function by running it with fixture data or auto-generated example input."""
    if not folder.exists() or not folder.is_dir():
        print(json.dumps({"ok": False, "error": f"folder not found: {folder}"}))
        raise SystemExit(2)

    script_name, _, func_name = target.partition(":")
    if not script_name or not func_name:
        print(json.dumps({"ok": False, "error": "target must be in the form script:function"}))
        raise SystemExit(2)

    env = parse_secrets_args(secrets or [])

    # Determine input data
    if fixture:
        if not fixture.exists():
            print(json.dumps({"ok": False, "error": f"fixture file not found: {fixture}"}))
            raise SystemExit(2)
        input_data = fixture.read_text(encoding="utf-8").strip()
    else:
        # Auto-generate from schema by running docs first
        try:
            script_path = resolve_script_path(folder, script_name)
        except FileNotFoundError as e:
            print(json.dumps({"ok": False, "error": str(e)}))
            raise SystemExit(2)
        payload = {"script_path": str(script_path), "require_marker": False}
        try:
            docs_out = uv_run_python_code(
                script_path=script_path,
                code=_DOCS_CODE,
                payload=payload,
                extra_env=env,
            )
            docs_data = json.loads(docs_out)
            # Find the matching function
            funcs = docs_data.get("functions", [])
            matched = None
            for fn in funcs:
                if fn.get("name") == func_name:
                    matched = fn
                    break
            if matched:
                input_data = _schema_to_example_input(matched.get("input_schema"))
            else:
                available = [fn.get("name", "?") for fn in funcs]
                print(json.dumps({
                    "ok": False,
                    "error": f"function '{func_name}' not found in {script_name}",
                    "available": available,
                }))
                raise SystemExit(2)
        except UVRunError:
            # Fallback: empty input
            input_data = "{}"

    # Show what we're testing
    print(f"Testing {target} with input: {input_data}", file=sys.stderr)

    # Run the function
    _cmd_run(folder, target, input_data, secrets)


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
    """Generate a reference document in SKILL.md-compatible format.

    Includes YAML frontmatter and per-function sections with full schemas.
    """
    lines: list[str] = []

    # Collect all function names for the description
    all_fn_names: list[str] = []
    for item in docs_out:
        script = Path(item.get("script", "")).stem
        for fn in item.get("functions") or []:
            all_fn_names.append(f"{script}:{fn.get('name', '')}")

    # YAML frontmatter
    lines.append("---")
    lines.append("name: supypowers-reference")
    lines.append(
        "description: Full schema reference for supypowers functions."
        " Use for detailed input/output schema lookup."
    )
    lines.append("---")
    lines.append("")

    lines.append("# Supypowers — Reference")
    lines.append("")

    for item in docs_out:
        script = item.get("script", "")
        script_stem = Path(script).stem
        err = item.get("error")

        fns = item.get("functions") or []
        if err:
            lines.append(f"## `{script_stem}`")
            lines.append("")
            lines.append(f"**Error:** `{err}`")
            lines.append("")
            continue
        if not fns:
            continue

        for fn in fns:
            name = fn.get("name", "")
            desc = (fn.get("description") or "").strip()
            in_schema = fn.get("input_schema")
            out_schema = fn.get("output_schema")

            lines.append(f"## `{script_stem}:{name}`")
            lines.append("")
            if desc:
                lines.append(desc)
                lines.append("")

            lines.append("```bash")
            example_input = _schema_to_example_input(in_schema)
            lines.append(f"supypowers run {script_stem}:{name} '{example_input}'")
            lines.append("```")
            lines.append("")

            if in_schema:
                lines.append("**Input schema**")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(in_schema, ensure_ascii=False, indent=2))
                lines.append("```")
                lines.append("")
            if out_schema:
                lines.append("**Output schema**")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(out_schema, ensure_ascii=False, indent=2))
                lines.append("```")
                lines.append("")

    return "\n".join(lines).rstrip() + "\n"


_SUPYPOWER_SKILL_PREFIX = "supypower-"

# Registry of AI coding tools and their skills folder conventions.
AI_TOOL_FOLDERS: list[dict[str, str]] = [
    {"name": "Claude Code", "detect": ".claude", "skills": ".claude/skills"},
    {"name": "Cursor", "detect": ".cursor", "skills": ".cursor/skills"},
    {"name": "Codex", "detect": ".agents", "skills": ".agents/skills"},
    {"name": "Copilot", "detect": ".copilot", "skills": ".copilot/skills"},
    {"name": "Windsurf", "detect": ".windsurf", "skills": ".windsurf/skills"},
]


def detect_ai_tool_folders(root: Path) -> list[dict[str, str]]:
    """Return AI tool entries whose detection folder exists under root."""
    return [entry for entry in AI_TOOL_FOLDERS if (root / entry["detect"]).is_dir()]


def _prompt_skill_output_dirs(
    root: Path,
    detected: list[dict[str, str]],
) -> list[Path]:
    """Interactive prompt for selecting which AI tool folders to populate with skills."""
    from rich.console import Console
    from rich.prompt import Prompt

    console = Console(stderr=True)

    if not detected:
        console.print(
            "[yellow]No AI tool folders detected[/yellow] "
            "(.claude, .cursor, .agents, .copilot, .windsurf)"
        )
        custom = Prompt.ask("Enter skills output path", default=".claude/skills")
        return [root / custom]

    console.print()
    console.print("[bold]Detected AI tool folders:[/bold]")
    console.print()
    for i, entry in enumerate(detected, 1):
        console.print(f"  [cyan]{i}[/cyan]. {entry['name']}  [dim]({entry['skills']}/)[/dim]")
    console.print()

    choice = Prompt.ask(
        "Select folders (comma-separated numbers, or 'a' for all)",
        default="a",
    )

    if choice.strip().lower() == "a":
        return [root / e["skills"] for e in detected]

    indices = []
    for part in choice.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(detected):
                indices.append(idx)

    if not indices:
        console.print("[yellow]Invalid selection, defaulting to all.[/yellow]")
        return [root / e["skills"] for e in detected]

    return [root / detected[i]["skills"] for i in indices]


def _write_skills_to_dir(output_dir: Path, skill_files: dict[str, str]) -> None:
    """Write skill files to a directory, cleaning up stale entries first."""
    import shutil

    output_dir.mkdir(parents=True, exist_ok=True)
    for existing in output_dir.iterdir():
        if existing.is_dir() and existing.name.startswith(_SUPYPOWER_SKILL_PREFIX):
            shutil.rmtree(existing)
        elif existing.is_file() and existing.name in ("supypowers.md", "SKILL.md"):
            existing.unlink()
    for dir_name, content in skill_files.items():
        skill_dir = output_dir / dir_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def _cmd_skills(
    folder: Path,
    secrets: list[str],
    output_path: Path | None,
    stdout: bool,
    select_all: bool = False,
    root: Path = Path("."),
) -> None:
    """Generate per-script skill files for AI agents."""
    from rich.console import Console

    env = parse_secrets_args(secrets or [])
    console_err = Console(stderr=True)

    # --- Phase 1: Generate skill content ---
    scripts_info: dict[str, list[dict]] = {}
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
                    scripts_info.setdefault(script_name, []).append(
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

    skill_files: dict[str, str] = {}
    for script_name in sorted(scripts_info.keys()):
        functions = scripts_info[script_name]
        dir_name = f"{_SUPYPOWER_SKILL_PREFIX}{script_name}"
        skill_files[dir_name] = _generate_skill_md(script_name, functions)

    if stdout:
        print("\n".join(skill_files.values()))
        return

    # --- Phase 2: Determine output directories ---
    if output_path:
        output_dirs = [Path(output_path)]
    else:
        detected = detect_ai_tool_folders(root)
        if select_all or not sys.stdin.isatty():
            if detected:
                output_dirs = [root / e["skills"] for e in detected]
            else:
                output_dirs = [root / ".claude/skills"]
        else:
            output_dirs = _prompt_skill_output_dirs(root, detected)

    # --- Phase 3: Write to each selected directory ---
    for output_dir in output_dirs:
        _write_skills_to_dir(output_dir, skill_files)

    # --- Phase 4: Output summary ---
    func_count = sum(len(fns) for fns in scripts_info.values())
    print(json.dumps({
        "ok": True,
        "skills": len(skill_files),
        "functions": func_count,
        "output_dir": str(output_dirs[0]),
        "output_dirs": [str(d) for d in output_dirs],
    }))

    console_err.print(
        f"[green]\u2713[/green] Generated [cyan]{len(skill_files)}[/cyan] skills "
        f"({func_count} functions) in [cyan]{len(output_dirs)}[/cyan] location(s)"
    )
    for output_dir in output_dirs:
        console_err.print(f"  [dim]{output_dir}/[/dim]")
        for dir_name in sorted(skill_files.keys()):
            console_err.print(f"    {dir_name}/SKILL.md")


def _generate_skill_md(script_name: str, functions: list[dict]) -> str:
    """Generate a SKILL.md for a single script following the Agent Skills format."""
    lines: list[str] = []

    # Build description from function actions
    func_names = [f"{fn['script']}:{fn['name']}" for fn in functions]
    actions = []
    for fn in functions:
        desc = fn.get("description", "").strip()
        if desc:
            first_sentence = desc.split(".")[0].strip().lower()
            if first_sentence and first_sentence not in actions:
                actions.append(first_sentence)

    display_name = script_name.replace("_", " ").title()
    action_list = ", ".join(actions[:4]) if actions else ", ".join(func_names)

    lines.append("---")
    lines.append(f"name: supypower-{script_name}")
    lines.append("description: >-")
    lines.append(
        f"  Run {display_name} functions via supypowers CLI. "
        f"Available: {action_list}. "
        f"Use when the user needs {display_name.lower()} functionality."
    )
    lines.append("---")
    lines.append("")

    lines.append(f"# {display_name}")
    lines.append("")
    lines.append("Execute tools: `supypowers run <script>:<function> '<json>'`")
    lines.append("")
    lines.append(
        'Output: `{"ok": true, "data": ...}` on success, '
        '`{"ok": false, "error": "..."}` on failure.'
    )
    lines.append("")

    for fn in functions:
        script = fn["script"]
        name = fn["name"]
        desc = fn.get("description", "").strip()
        in_schema = fn.get("input_schema")

        lines.append(f"### {script}:{name}")
        lines.append("")
        if desc:
            lines.append(desc)
            lines.append("")

        # Example invocation
        example_input = _schema_to_example_input(in_schema)
        lines.append("```bash")
        lines.append(f"supypowers run {script}:{name} '{example_input}'")
        lines.append("```")
        lines.append("")

        # Input field table
        if in_schema:
            props = in_schema.get("properties", {})
            required = set(in_schema.get("required", []))
            if props:
                lines.append("| Field | Type | Required | Description |")
                lines.append("|-------|------|----------|-------------|")
                for field_name, field_info in props.items():
                    field_type = field_info.get("type", "any")
                    field_desc = field_info.get("description", "")
                    is_req = "yes" if field_name in required else "no"
                    lines.append(f"| `{field_name}` | {field_type} | {is_req} | {field_desc} |")
                lines.append("")

    return "\n".join(lines)


def _generate_skills_markdown(functions: list[dict]) -> str:
    """Generate combined skills markdown. Backwards-compat wrapper for --stdout."""
    scripts_info: dict[str, list[dict]] = {}
    for fn in functions:
        scripts_info.setdefault(fn["script"], []).append(fn)
    parts = []
    for script_name in sorted(scripts_info.keys()):
        parts.append(_generate_skill_md(script_name, scripts_info[script_name]))
    return "\n".join(parts)


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

# ── stdout isolation ──────────────────────────────────────────────────────────
# Third-party libraries (litellm, etc.) may print debug/info messages to stdout.
# Since the runner protocol uses stdout for JSON results, any stray output
# corrupts parsing.  We redirect stdout to stderr before loading the target
# module so all library noise goes to stderr.  Only _emit() restores the real
# stdout momentarily to write the JSON result.

_real_stdout = sys.stdout

def _emit(obj):
    # Write obj as JSON to the real stdout (bypassing redirect).
    _real_stdout.write(json.dumps(obj, ensure_ascii=False))
    _real_stdout.write("\n")
    _real_stdout.flush()

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

    # Redirect stdout → stderr so library prints don't corrupt our JSON output
    sys.stdout = sys.stderr

    mod = _load_module_from_path(script_path)
    fn = getattr(mod, fn_name, None)
    if fn is None or not callable(fn):
        _emit({"ok": False, "error": f"function not found: {fn_name}"})
        return 2

    sig = inspect.signature(fn)
    params = list(sig.parameters.values())

    try:
        if len(params) == 0:
            # No-input function — call directly
            result = fn()
        elif len(params) == 1 and params[0].name == "input":
            # Standard supypower: one `input` param with Pydantic model
            param = params[0]
            hints = _resolved_type_hints(fn, mod)
            ann = hints.get(param.name, param.annotation)
            raw = _parse_input(input_data)

            if not _is_pydantic_model(ann):
                _emit({"ok": False, "error": "input must be a Pydantic BaseModel type annotation"})
                return 2
            if not isinstance(raw, dict):
                _emit({"ok": False, "error": "input_data must be an object mapping for the input model"})
                return 2
            inp = ann.model_validate(raw) if hasattr(ann, "model_validate") else ann.parse_obj(raw)
            result = fn(inp)
        else:
            _emit({"ok": False, "error": "function must have zero parameters or exactly one parameter named `input`"})
            return 2

        out = _model_to_jsonable(result)
        try:
            json.dumps(out)
        except Exception:
            out = str(out)
        _emit({"ok": True, "data": out})
        return 0
    except Exception as e:
        _emit({"ok": False, "error": str(e)})
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

        # Accept zero-param functions or one-param functions with `input` as Pydantic model
        if len(params) == 0:
            if require_marker and not _has_superpower_decorator(script_path, name):
                continue
            hints = _resolved_type_hints(obj, mod)
            ann_out = hints.get("return", sig.return_annotation)
            fns.append({
                "name": name,
                "description": inspect.getdoc(obj) or "",
                "input_schema": None,
                "output_schema": _schema_for_model(ann_out) if _is_pydantic_model(ann_out) else None,
            })
        elif len(params) == 1 and params[0].name == "input":
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


_HELLO_MD = """---
name: supypowers-authoring
description: How to create supypowers scripts. Use when you need to build a new Python function for the supypowers CLI.
---

# Creating Supypowers Scripts

Each supypowers script is a self-contained Python file in the `powers/` folder.
Scripts are run via `supypowers run <script>:<function> '<json>'` and always return JSON.

## Quick Start

```bash
supypowers new my_tool                                 # Create from template
supypowers run my_tool:my_tool '{\"value\": \"test\"}'   # Run it
supypowers skills                                      # See all functions
```

## Template

```python
# /// script
# dependencies = [
#   \"pydantic\",
# ]
# ///
from pydantic import BaseModel, Field


class MyInput(BaseModel):
    param1: str = Field(..., description=\"Description of param1\")
    param2: int = Field(default=0, description=\"Optional with default\")


class MyOutput(BaseModel):
    success: bool
    result: str | None = None
    error: str | None = None


def my_function(input: MyInput) -> MyOutput:
    \"\"\"One-line description of what this function does.\"\"\"
    try:
        return MyOutput(success=True, result=f\"Got {input.param1}\")
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
| 8 | Use `Field(..., description=\"...\")` for all fields |

## Common Patterns

### HTTP requests

```python
# /// script
# dependencies = [\"pydantic\", \"httpx\"]
# ///
import httpx
from pydantic import BaseModel, Field

class FetchInput(BaseModel):
    url: str = Field(..., description=\"URL to fetch\")

class FetchOutput(BaseModel):
    status: int
    body: str

def fetch_url(input: FetchInput) -> FetchOutput:
    \"\"\"Fetch a URL and return its contents.\"\"\"
    resp = httpx.get(input.url)
    return FetchOutput(status=resp.status_code, body=resp.text[:1000])
```

### Secrets

```bash
supypowers run my_script:my_func '{}' --secrets API_KEY=sk-xxx
supypowers run my_script:my_func '{}' --secrets .env
```

Access in code: `api_key = os.environ.get(\"API_KEY\")`

### Optional fields

```python
class SearchInput(BaseModel):
    query: str = Field(..., description=\"Search query (required)\")
    limit: int = Field(default=10, description=\"Max results\")
```

### Error handling

```python
class ProcessOutput(BaseModel):
    success: bool
    result: str | None = None
    error: str | None = None

def process(input: ProcessInput) -> ProcessOutput:
    \"\"\"Process something.\"\"\"
    try:
        return ProcessOutput(success=True, result=do_work(input.data))
    except Exception as e:
        return ProcessOutput(success=False, error=str(e))
```

### Media output (images, audio, etc.)

Tools that generate media files SHOULD include a `_media` list in their output:

```python
class GenOutput(BaseModel):
    success: bool
    _media: list[dict] = Field(default_factory=list, description=\"Generated media files\")

def generate(input: GenInput) -> GenOutput:
    \"\"\"Generate an image.\"\"\"
    path = Path(input.output_dir) / f\"{hash}.png\"
    # ... generate file ...
    return GenOutput(
        success=True,
        _media=[{\"path\": str(path.resolve()), \"type\": \"image\"}],
    )
```

Each `_media` entry: `{\"path\": \"/absolute/path.png\", \"type\": \"image\"}`.
Valid types: `image`, `audio`, `video`, `document`.
All paths MUST be absolute. The tool MUST create `output_dir` if it doesn't exist.

## Troubleshooting

| Error | Fix |
|-------|-----|
| `function not found` | Check spelling — case-sensitive |
| `input must be a Pydantic BaseModel` | Add type annotation: `def func(input: MyModel)` |
| `function must accept exactly one parameter` | Only one param named `input` allowed |
| Import error | Add the package to `# /// script` dependencies |
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
    # For media-generating tools, include:
    # _media: list[dict] = Field(default_factory=list, description="Generated media files")
    # Each entry: {{"path": "/absolute/path.png", "type": "image"}}


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

