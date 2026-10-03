# CLAUDE.md

Guidance for Claude Code when working in a project started from this template.

## This project

`Watershed_generator_TDX_Pourpoint` — vector watershed delineation for dam
outlets with the [pourpoint](https://github.com/CooperBigFoot/pourpoint)
engine (staged API) on the TDX-Hydro HFX dataset on S3 (Hetzner). Everything
lives in `Module/ExtractWatershedPourpoint.py`; its docstring and `README.md`
→ "Input and outputs" describe inputs, outputs and modes.

- The dataset has **no D8 raster**, so the engine runs with `refine=False`;
  results are whole drainage units. Snapping is `distance-first` (closest
  stream reach, default radius 1000 m).
- **Credentials:** AWS profile `pourpoint-hfx` in `~/.aws`. Never put keys
  in code, docs, logs or chat, and never ask the user to paste the secret
  key — they enter it locally (`RUN_COMMANDS.md` → "S3 credentials").
  pourpoint's S3 layer reads `AWS_*` env vars, not `~/.aws`, so the script
  resolves the profile with boto3 and exports it in-process.
- **Outputs per dam** (separate GPKGs under `Plot/`): sub-basins (saved from
  the staged `pre_merge_units` step before `dissolve`), watershed, upstream
  river network; each also merged into `<name>_*_merged.gpkg`. The watershed
  file is written last and marks a dam as done.
- Run commands from the project folder; reruns skip finished dams unless
  `--overwrite`. Do not copy files from the older `Watershed_generator_TDX`
  project (it was only a reference for the logic).
- Keep `RUN_COMMANDS.md`, `README.md` and the script docstring in sync when
  options or outputs change.

## Package management

- **uv only.** Never use `pip`, `pip install`, `conda`, or `python -m venv` directly.
  - Add a dependency: `uv add <package>`
  - Remove a dependency: `uv remove <package>`
  - Install/sync environment: `uv sync`
  - Run any script: `uv run python Module/your_script.py`
- Never edit `.venv` by hand and never hand-edit dependency versions in
  `pyproject.toml` — use `uv add`/`uv remove` so the lockfile stays consistent.

## Project structure

- `Module/` — all Python scripts/source code go here.
- `Data/` — input data (not tracked in git).
- `Output/` — generated results (not tracked in git).
- `Plot/` — generated figures/plots (not tracked in git).
- `Resources/` — reference/support files.
- `pyproject.toml` — project metadata and dependencies (uv-managed).
- `CHANGELOG.md` — notable changes, following Keep a Changelog.
- `RUN_COMMANDS.md` — quick command reference; keep it in sync with reality.

`[tool.uv] package = false` is set intentionally (scripts project, not an
installable package) — don't remove it.

## Conventions

- Python `>=3.13`.
- `tkinter` is stdlib — never add it as a dependency.
- Keep `Data/`, `Output/`, `Plot/` out of git (already in `.gitignore`);
  don't change that without asking.
- This project follows SemVer. When a change is worth recording, add a
  bullet under `[Unreleased]` in `CHANGELOG.md`.

## General rules

- Don't add error handling, abstractions, or config options for cases that
  can't happen — keep scripts direct and readable.
- Don't introduce new top-level folders or restructure the template layout
  without asking first.
- Prefer editing existing scripts in `Module/` over creating new ones for
  small changes.

## Memory (mnema)

This project uses [mnema](https://github.com/front-depiction/mnema) for
durable, project-specific memory. Read mnema's own `AGENTS.md` for the full
usage contract (`remember` / `ask` / `keep`) — this section only covers how
it's scoped within this template.

One root store, everything else mounted onto it as a leaf. This project's
own store mounts nothing itself — it only holds this project's own writes:

- **root** (`~/.mnema`, mnema's own default store — plain `mnema ask` with
  no `--store` flag hits this) — mounts `doctrine`, every `library-*`
  shard, and every project (including this one, as `project-<Name>`). Ask
  root for anything that should span doctrine + research + prior projects.
- **local** (`./Resources/.mnema`) — this project's own decisions only.
  The only store `remember` ever writes to. Mounts nothing of its own.
- **`doctrine`** (`~/MyProjects/MyPython/.mnema-doctrine`) — cross-project
  conventions and recurring gotchas, mounted on root once, not per project.
- **`library`** (`~/.mnema-vaults/e-library/*`) — the research corpus,
  sharded into ~165 vaults (`library-ICOLD-3`, `library-WB-4`, ...) since
  one store's capacity is far smaller than the whole corpus. Also mounted
  on root once, never duplicated into a project.

One-time setup for a new project (see `RUN_COMMANDS.md`):

```bash
mnema --store ./Resources/.mnema init
./register-project.sh   # attaches this project to root as project-<Name>;
                         # bootstraps root (doctrine + library) on first-ever use
```

When to use it:

- **Before implementing a non-trivial design choice** (see "Confirm the
  design before implementing" below, and "Stage zero" in global
  instructions), ask root first: `mnema ask "<question>"` (no `--store` —
  root is the CLI default). A purely mechanical question that doesn't need
  doctrine or the literature can scope to just this project with
  `mnema --store ./Resources/.mnema ask --local "..."`.
- **After a design is confirmed**, remember the conclusion, not the
  discussion that produced it, into the LOCAL store (writes never target
  root or any vault): `mnema --store ./Resources/.mnema remember "<decision
  and why, one belief per entry>"`.
- **If something learned here is genuinely reusable across projects**
  (not case-specific), promote it deliberately — don't assume it belongs
  in doctrine just because it worked here:
  `mnema --store ~/MyProjects/MyPython/.mnema-doctrine remember "<reusable convention>"`.

## Working style

- **Confirm the design before implementing, for anything non-trivial.**
  When there's more than one reasonable way to build a feature, or a
  design choice has real consequences (what a default should be, how an
  edge case should behave, what gets validated vs. silently allowed),
  propose the approach and wait for confirmation before writing code.
  Don't let an autonomous multi-step plan run through several files on an
  unconfirmed assumption.
- **Verify by actually running the code, not just by reading it or
  syntax-checking it.** Run the real script against real (or realistic
  test) data before calling a change complete. A file that only passes
  `python -m py_compile`/linting has not been verified. If the real
  script can't be run end-to-end (missing data, missing external
  service), say so explicitly and test as much of the real logic as
  possible instead of skipping verification silently.
- **When two scripts need the same logic, factor it out into one shared,
  importable function or module — don't duplicate it.** Duplicated logic
  drifts the first time one copy gets fixed and the other doesn't.
- **When asked to review or audit code, actually read every relevant
  file.** Don't just grep for the one issue already mentioned — the most
  useful findings are usually the ones nobody knew to look for yet.
- **Don't rely on memory of a file's contents from earlier in the
  session — re-read it before making claims about it or building on it.**
  This matters most in long sessions, where a file may have changed since
  it was last read, or memory of its exact contents may be imprecise.
- **Git is not a silent "finishing step."** You have real commit/push
  access in this environment — use it deliberately, not automatically.
  Stage changes and propose a commit message, but wait for explicit
  confirmation before committing, and confirm again before pushing. Keep
  commit messages concise unless asked for more detail.