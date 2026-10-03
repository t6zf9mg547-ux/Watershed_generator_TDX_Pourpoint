# Run Commands

Quick reference for the standard commands in this project. All Python
commands are run through `uv run` so they use the project's managed
virtual environment.

## Setup (once, after cloning or copying this template)

```bash
uv sync
```
Creates `.venv` and installs everything listed in `pyproject.toml`.

## Running a script

Always run from this project's folder (`cd ~/MyProjects/MyPython/Watershed_generator_TDX_Pourpoint`),
otherwise `Module/...` won't be found.

```bash
uv run python Module/ExtractWatershedPourpoint.py
```
Opens a file picker (starts in `Data/`) and a snap-radius dialog; if results
already exist for the chosen CSV it asks whether to overwrite them.

Non-interactive batch (no dialogs):
```bash
uv run python Module/ExtractWatershedPourpoint.py --csv Data/Morocco.csv
uv run python Module/ExtractWatershedPourpoint.py --csv Data/Morocco.csv --radius 3000
uv run python Module/ExtractWatershedPourpoint.py --csv Data/Morocco.csv --overwrite
```
`--radius` is the snap search radius in metres (default 1000). Without
`--overwrite`, dams that already have results are skipped; with it, every
dam is recomputed and all outputs replaced.

Single-point test (prints area/terminal unit, saves GeoJSON to `Plot/`):
```bash
uv run python Module/ExtractWatershedPourpoint.py --test 47.3769 8.5417
```

Outputs per CSV `<name>`: sub-basin, watershed and river-network GPKGs per
dam plus `*_merged.gpkg` for each, under `Plot/`; the CSV and diagnostics
under `Output/`. See `README.md` → "Input and outputs".

## Managing dependencies

Add a package:
```bash
uv add <package>
```

Remove a package:
```bash
uv remove <package>
```

Re-sync the environment after manually editing `pyproject.toml`:
```bash
uv sync
```

## S3 credentials (pourpoint-hfx profile)

Install the AWS CLI (no AWS account needed — the keys belong to a third-party
S3-compatible store):
```bash
brew install awscli
aws --version
```

Non-secret settings (safe to type anywhere):
```bash
aws configure set region fsn1 --profile pourpoint-hfx
aws configure set endpoint_url https://fsn1.your-objectstorage.com --profile pourpoint-hfx
aws configure set s3.addressing_style path --profile pourpoint-hfx
aws configure set aws_access_key_id 2ZWQNKOJF9107MLQSZI0 --profile pourpoint-hfx
```

Secret key — run in YOUR terminal; input is hidden and never enters shell
history, `ps`, or chat (zsh builtins only):
```bash
read -s "SK?Secret key: "; echo; printf 'aws_secret_access_key = %s\n' "$SK" >> ~/.aws/credentials; unset SK; chmod 600 ~/.aws/credentials
```

Run the secret-key command **once**: it appends, and a duplicated
`aws_secret_access_key` line makes botocore fail with "Unable to parse
config file". If that happens, delete the extra line from
`~/.aws/credentials`.

Then test with the single-point command under "Running a script".

## Versioning and releases

This project follows [SemVer](https://semver.org/) (`MAJOR.MINOR.PATCH`).
See the "Versioning" section in `README.md` for the full convention.

When a change is worth recording, add a bullet under `[Unreleased]` in
`CHANGELOG.md` -- no command needed, just edit the file.

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
   (confirm your default branch name first -- `git branch -vv` --
   rather than assuming `main`.)

## Memory (mnema)

See `CLAUDE.md` → "Memory (mnema)" for what each store is and when to use
it. Commands only, here.

One-time, per new project:
```bash
mnema --store ./Resources/.mnema init
mnema vault add ~/MyProjects/MyPython/.mnema-doctrine --name doctrine
./mount-library.sh   # mounts every library-<shard> vault (auto-discovered)
```

Day to day:
```bash
mnema --store ./Resources/.mnema ask "<question>"                # local + doctrine + all library shards
mnema --store ./Resources/.mnema ask --local "<question>"        # this project only
mnema --store ./Resources/.mnema remember "<decision and why>"
```

The library corpus is sharded into ~166 vaults (`library-ICOLD-1`, `library-WB-4`,
...) rather than one `library` vault -- a single store's capacity is ~D live
entries, and the corpus is far larger than any sane `--dim` can hold in one
store. There's no single name to `--except` anymore; to keep doctrine but skip
the whole corpus for one query:
```bash
mnema --store ./Resources/.mnema ask $(mnema vault list | awk '{print $1}' | grep '^library-' | sed 's/^/--except /') "<question>"
```

If it's slow (~10s per call), start the warm-model daemon once per machine:
```bash
mnema serve &
```

## Starting a new project from this template

```bash
cp -r Template ~/path/to/NewProjectName
cd ~/path/to/NewProjectName
```
Then edit `pyproject.toml` (`name`, `description`, reset `version` to
`0.1.0`) before running `uv sync`. See `README.md` for the full
walkthrough.
