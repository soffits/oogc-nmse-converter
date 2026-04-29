# AGENTS.md

## Project Purpose

`oogc-nmse-converter` converts OOGC / NMS Model IO `.nmsship` ZIP exports into NMSE-compatible wrapper JSON for import into `vectorcmdr/NMSE`.

## Architecture

- Python package lives in `src/oogc_nmse_converter/`.
- `converter.py` contains conversion, ZIP reading, member extraction, metadata, and validation logic.
- `cli.py` exposes the `oogc-nmse-convert` command-line interface.
- Tests live in `tests/` and cover converter and CLI behavior.

## Package Manager And Commands

- Package manager: `uv` with `pyproject.toml` and `uv.lock`.
- Runtime dependencies: Python standard library only.
- Test dependency: `pytest`, installed through the `dev` dependency group.
- Run tests: `uv run pytest`.
- Run CLI from the workspace: `uv run oogc-nmse-convert path/to/ship.nmsship`.

## Coding Rules

- Keep changes minimal and focused; avoid implementation edits unless needed for the requested task or a serious issue.
- Preserve stdlib-only runtime code; do not add runtime dependencies without explicit approval.
- Follow the existing simple functional style, type hints, and `ConversionError` error reporting.
- Keep line length near the configured Ruff limit of 100 characters.
- Add or update pytest tests when behavior changes.

## Security Boundaries

- Treat `.nmsship` files as untrusted ZIP input data.
- Never use unsafe archive extraction for user-controlled ZIP members.
- Avoid path traversal: only read or write explicitly allowed member names such as `so.json`, `ccd.json`, and `objects.json`.
- Do not execute data from ship packages; parse it as JSON only.
- Keep output overwrite protections unless a user explicitly opts in with `--force`.

## Commit Convention

- Use concise Conventional Commit-style messages, matching the existing history, for example `feat: add OOGC NMSE converter`.

## License

This project is licensed under `AGPL-3.0-only`; keep derivative work compatible with that license.
