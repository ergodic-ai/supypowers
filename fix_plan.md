# Fix Plan: Stdout Isolation, Media Tools Convention, Folder Rename

## Problem Summary

Three related issues need to be addressed:

1. **Stdout pollution**: Third-party libraries (e.g. litellm prints a colored "Provider List" URL) can write to stdout, corrupting the runner's JSON output. The current protocol assumes stdout contains *only* the JSON result, but tool authors cannot control what their dependencies print.

2. **No media tool convention**: Tools that generate images (or other media files) need a documented contract so consumers know how to detect and display the generated files. Currently this is ad-hoc (`images` field, `_images` field, `path` field).

3. **Folder name collision**: The default tool folder is `supypowers/`, which is also the name of the installed Python package. When projects use an editable install (common during development), the local `supypowers/__init__.py` shadows the installed package, breaking the `supypowers` CLI entirely.

---

## Change 1: Stdout Isolation in the Runner

**Files:** `src/supypowers/cli.py` (`_RUNNER_CODE` string)

### What

Redirect `sys.stdout` to `sys.stderr` before loading the target module and executing the function. Only the final JSON result is written to the real stdout via a dedicated `_emit()` helper.

### Why

The runner protocol uses stdout as the data channel. Any `print()` call — whether from the tool code or, more commonly, from third-party libraries — corrupts the JSON and causes `"runner did not emit valid JSON"` errors. This is a systemic problem: every new dependency is a potential source of stdout noise.

### How

In `_RUNNER_CODE`:

```python
_real_stdout = sys.stdout

def _emit(obj):
    # Write obj as JSON to the real stdout (bypassing redirect).
    _real_stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    _real_stdout.flush()

def main():
    payload = json.loads(sys.stdin.read())
    # ... parse payload ...

    # Redirect stdout -> stderr BEFORE loading the module.
    # All library prints (litellm, httpx, warnings, etc.) go to stderr.
    sys.stdout = sys.stderr

    mod = _load_module_from_path(script_path)
    # ... validate, execute ...

    _emit({"ok": True, "data": out})   # only this hits real stdout
```

Replace all `print(json.dumps(...))` calls in `main()` with `_emit(...)`.

### Defense in depth (consumer side)

In `_cmd_run()` (the outer CLI layer), if `json.loads(out)` fails, try extracting the last line that looks like JSON before giving up. This handles edge cases where the redirect doesn't catch everything (e.g. C extensions writing directly to fd 1):

```python
try:
    parsed = json.loads(out)
except json.JSONDecodeError:
    # Try last non-empty line (in case of stray output before the JSON)
    for line in reversed(out.strip().splitlines()):
        try:
            parsed = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    else:
        # Truly unparseable
        print(json.dumps({"ok": False, "error": "runner did not emit valid JSON", "raw": out}))
        raise SystemExit(1)
```

### Tests

- Add a test tool that does `print("NOISE")` before returning, verify the runner still returns clean JSON.
- Add a test with a dependency that prints to stdout during import.

---

## Change 2: Media Tools Convention

**Files:** `README.md` or new `docs/media_tools.md`, plus update the authoring skill text in `cli.py`

### What

Document a standard convention for tools that produce media files (images, audio, video, PDFs):

### Convention

1. **Output field `_media`**: Tools that generate media files SHOULD include a `_media` list in their output model. Each entry is an object:

   ```json
   {
     "_media": [
       {"path": "/absolute/path/to/file.png", "type": "image"},
       {"path": "/absolute/path/to/audio.wav", "type": "audio"}
     ]
   }
   ```

   Valid types: `image`, `audio`, `video`, `document`.

2. **Backward compat**: Consumers SHOULD also check for the legacy patterns:
   - `images` or `_images`: list of image file paths (flat string list)
   - `path` with an image extension when `ok: true`

3. **File naming**: Use content-hash filenames (e.g. `{sha256[:12]}.png`) for deduplication. Consumers may re-request the same generation and should get the same file back.

4. **Output directory**: Media tools SHOULD accept an `output_dir` parameter with a sensible default (e.g. `generated_images/`). The tool MUST create the directory if it doesn't exist.

5. **Absolute paths**: All paths in the output MUST be absolute so consumers don't need to guess the working directory.

### Where to document

- Add a "Media Tools" section to the authoring skill/guide (`_AUTHORING_SKILL` in cli.py)
- Add to `README.md` under a "Conventions" section
- Update the `supypowers new` template to include a commented example of `_media` usage

### Consumer side (supyagent)

Update `detect_images_in_tool_result()` in `supyagent/utils/media.py` to also check for the `_media` field:

```python
# Strategy 0: structured _media list
if "_media" in result:
    for entry in result["_media"]:
        if entry.get("type") == "image" and isinstance(entry.get("path"), str):
            ...
```

---

## Change 3: Rename Default Folder from `supypowers` to `powers`

**Files:** Broad rename across `cli.py`, `README.md`, tests, examples, skill text

### What

Change the default tool folder name from `supypowers/` to `powers/`.

### Why

The folder name `supypowers/` collides with the Python package name `supypowers`. When a project is installed in editable mode (`pip install -e .` or `uv pip install -e .`), the project root is added to `sys.path`. If the project has `supypowers/__init__.py` (common — Python treats any directory with `__init__.py` as a package), it shadows the installed `supypowers` package, breaking `from supypowers.cli import app` and the entire CLI.

`powers/` is short, clear, and cannot collide with the package name.

### Scope

1. **`cli.py`**: Change `SUPYPOWERS_FOLDER = "supypowers"` to `POWERS_FOLDER = "powers"`. Update all references:
   - `_resolve_supypowers_folder()` -> `_resolve_powers_folder()`
   - Help text, error messages, hints
   - `_cmd_init`, `_cmd_new` folder creation
   - Skill text and authoring guide strings

2. **Backward compatibility**: Check for both `powers/` and `supypowers/` (fallback). If `powers/` doesn't exist but `supypowers/` does, use `supypowers/` and emit a deprecation warning to stderr:
   ```python
   def _resolve_powers_folder(root: Path, *, use_examples: bool) -> Path:
       powers_dir = (root / POWERS_FOLDER).resolve()
       if powers_dir.exists():
           return powers_dir
       # Fallback to legacy name
       legacy_dir = (root / "supypowers").resolve()
       if legacy_dir.exists():
           print("Warning: 'supypowers/' is deprecated, rename to 'powers/'", file=sys.stderr)
           return legacy_dir
       return powers_dir  # return expected path (will fail later with clear error)
   ```

3. **`supypowers init`**: Create `powers/` instead of `supypowers/`.

4. **`supypowers new`**: Create scripts in `powers/`.

5. **README.md**: Update all folder references.

6. **Examples**: Rename `examples/supypowers/` to `examples/powers/`.

7. **Tests**: Update paths in test fixtures.

8. **Consumers (supyagent)**: Update references in `supyagent/cli/main.py` and any agent configs that reference `supypowers/`. The `supypowers` CLI command name stays the same — only the folder changes.

### Migration

No automated migration tool needed. Users rename the folder:
```bash
mv supypowers powers
```

The backward-compat fallback means existing projects continue to work with a deprecation warning.

---

## Implementation Order

1. **Stdout isolation** (Change 1) — Most critical, fixes a live bug. Small, contained change.
2. **Media convention** (Change 2) — Documentation + small code change. Can be done in parallel.
3. **Folder rename** (Change 3) — Largest scope, needs careful find-and-replace + backward compat. Do last.

## Testing Checklist

- [ ] `supypowers run` returns clean JSON even when tool dependencies print to stdout
- [ ] `supypowers run` returns clean JSON with libraries that print during import
- [ ] Consumer (`tools.py`) parses results correctly from noisy tools
- [ ] `_media` field detected by `detect_images_in_tool_result()`
- [ ] `supypowers init` creates `powers/` folder
- [ ] `supypowers run` finds scripts in `powers/`
- [ ] `supypowers run` falls back to `supypowers/` with deprecation warning
- [ ] All existing tests pass after rename
- [ ] `supypowers` CLI works when project has `powers/__init__.py` (no shadowing)
