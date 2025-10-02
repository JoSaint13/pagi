# Repository Guidelines

## Project Structure & Module Organization
- `panda_agi/` is the SDK package: `client/` handles HTTP + streaming, `envs/` defines execution backends, `handlers/` wires events, `tools/` exposes agent actions, `train/` hosts orchestration helpers.
- `panda_agi/tests/` mirrors the package layout; add tests next to the module they cover.
- `examples/` provides runnable references (`quickstart.py`, `cli.py`, `ui/` Docker app); `docs/` stores assets consumed by README and external docs.
- Keep experimental workspaces and generated artifacts outside the repo root.

## Build, Test, and Development Commands
- `uv pip install -e ".[dev]"` sets up runtime and contributor dependencies.
- `uv run pytest` runs the full suite; add `-k <pattern>` or `-m <marker>` during iteration.
- `uv run python examples/quickstart.py` validates core agent flows; `cd examples/ui && ./start.sh` boots the Docker UI for manual end-to-end checks.

## Coding Style & Naming Conventions
- Auto-format with `uv run black .` and lint via `uv run flake8`; CI expects both.
- Use 4-space indentation, snake_case for functions and modules, CamelCase for classes, and typed signatures for public APIs.
- Document modules with concise docstrings and prefer `logging.getLogger(...)` over `print` for runtime feedback.

## Testing Guidelines
- Author `pytest` cases under `panda_agi/tests/`, naming files `test_<module>.py` and functions `test_<behavior>` for discoverability.
- Mock external services (HTTP, Docker, S3) so tests stay deterministic and offline-friendly.
- Mark async tests with `@pytest.mark.asyncio`, keep timeouts strict, and exercise error branches alongside happy paths.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat:`, `fix:`, `chore:`); keep subjects under 72 characters and describe changes in the imperative mood.
- Rebase on main before opening a PR, squash noisy WIP commits, and include reproduction or validation steps in the description.
- Link tracking issues, attach screenshots for UI tweaks, and confirm `uv run pytest` plus linting before requesting review.

## Security & Configuration Tips
- Store `PANDA_AGI_KEY` and optional `TAVILY_API_KEY` in env vars or a local `.env` kept out of version control.
- When running agents against local directories, point `LocalEnv` to disposable paths and purge generated files prior to committing.
