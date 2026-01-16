# supypowers

Run self-contained Python scripts (with `uv` script dependencies) as callable, schema-documented functions.

## Install

```bash
pip install supypowers
```

Note: the CLI expects [`uv`](https://github.com/astral-sh/uv) to be installed on your machine (it shells out to `uv run`).

## Release to PyPI (recommended: GitHub Actions)

- Create a PyPI project using **Trusted Publishing** for your GitHub repo.
- Tag a release:

```bash
git tag v0.1.0
git push --tags
```

The workflow in `.github/workflows/publish.yml` will build and publish `dist/*` to PyPI.

## Run (no venv)

From this repo root:

```bash
uv run supypowers examples docs
uv run supypowers examples run exponents:compute_sqrt \"{'x': 9}\" --secrets .env --secrets API_KEY=abc
```

From anywhere:

```bash
uv run --project /Users/andre/ergodic/superpowers supypowers examples docs
```

## Install `supypowers` on your PATH (so you can run `supypowers ...`)

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

## Notes

- The CLI executes target scripts **only** via `uv run <script.py> ...` (no imports into the CLI process).
