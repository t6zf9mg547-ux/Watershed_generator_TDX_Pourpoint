# Watershed_generator_TDX_Pourpoint

Vector watershed delineation for dam outlets using the
[pourpoint](https://github.com/CooperBigFoot/pourpoint) engine against the
TDX-Hydro HFX dataset hosted on S3 (Hetzner object storage). The dataset has
no D8 raster auxiliary, so results are whole-drainage-unit (vector) watersheds.

- `Module/ExtractWatershedPourpoint.py` — CSV batch mode (file picker) or
  `--test LAT LON` single-point mode. See the script docstring.

## S3 credentials

Credentials live in the local AWS profile `pourpoint-hfx`
(`~/.aws/credentials`, region/endpoint in `~/.aws/config`) — never in the
repo. The script resolves the profile with boto3 at runtime. See
`RUN_COMMANDS.md` → "S3 credentials" for the setup commands.

---

*The rest of this file is the original template documentation.*

## Python Project Template

A reusable starting point for Python projects using [uv](https://docs.astral.sh/uv/) for dependency management, geared toward geospatial/data-analysis scripts (geopandas, pandas, shapely, etc.).

See `RUN_COMMANDS.md` for a quick reference of every standard command (setup, running scripts, dependencies, versioning/releases) without having to dig through this file.

## What's included
Template/
├── Data/            # place input data here (not tracked in git)
├── Module/          # your Python scripts go here
├── Output/          # generated results (not tracked in git)
├── Plot/            # generated figures/plots (not tracked in git)
├── Resources/       # reference/support files, incl. this project's
│                     mnema memory store (Resources/.mnema) — see below
├── pyproject.toml   # project metadata + dependencies (uv-managed)
├── CHANGELOG.md     # record of notable changes, by version
├── RUN_COMMANDS.md  # quick reference for standard commands
├── CLAUDE.md        # guidance for Claude Code, incl. memory usage
└── .gitignore       # excludes venv, cache files, Data/Output/Plot, OS junk, etc.

## Memory

Each project gets its own [mnema](https://github.com/front-depiction/mnema)
store at `Resources/.mnema`, plus read-only vaults for cross-project
conventions and the research library. See `CLAUDE.md` → "Memory (mnema)"
for the scoping model and `RUN_COMMANDS.md` for the exact commands.

## How to start a new project from this template

```bash
cp -r Template ~/path/to/NewProjectName
cd ~/path/to/NewProjectName
```

Then edit `pyproject.toml`:
- Update `name` (e.g. `"extract-drainage-system"`)
- Update `description` to describe the new project
- Reset `version` to `"0.1.0"` if it isn't already (a fresh project starts its own version history, separate from the template's)

Install dependencies and create the virtual environment:
```bash
uv sync
```

Run any script using the project's environment:
```bash
uv run python Module/your_script.py
```

## Default dependencies

- geopandas
- pandas
- fiona
- shapely
- numpy
- pyproj
- pyarrow (needed if reading/writing GeoParquet files)

Add or remove packages as the new project needs:
```bash
uv add <package>
uv remove <package>
```

## Notes

- `tkinter` (used for file/folder selection dialogs in some scripts) is part of the Python standard library and does not need to be added as a dependency — just make sure your Python installation includes it (standard on macOS python.org / Homebrew builds).
- GDAL must be installed at the system level for `fiona`/`geopandas` to work: `brew install gdal`.
- `[tool.uv] package = false` in `pyproject.toml` marks this as a scripts project rather than an installable package — required so `uv sync`/`uv add` don't try (and fail) to build a wheel.
- `Data/`, `Output/`, and `Plot/` are excluded from git by default, since they typically hold large or regenerated files. Adjust `.gitignore` per-project if you want any of them tracked.

## Versioning

This project follows [SemVer](https://semver.org/) (`MAJOR.MINOR.PATCH`):
increment `MAJOR` for breaking changes, `MINOR` for new backward-compatible
features, `PATCH` for bug fixes.

When a change is worth recording:
1. Add a bullet under `[Unreleased]` in `CHANGELOG.md`.

When it's time to tag a release:
1. Update `version` in `pyproject.toml`.
2. Move the `[Unreleased]` entries in `CHANGELOG.md` under a new
   `## [X.Y.Z] - YYYY-MM-DD` heading.
3. Commit and tag:
   ```bash
   git commit -am "Bump version to X.Y.Z"
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin main --tags
   ```
   (confirm your default branch name first — `git branch -vv` — rather
   than assuming `main`.)