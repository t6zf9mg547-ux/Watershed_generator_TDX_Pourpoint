# Changelog

All notable changes to a project derived from this template should be
recorded here, following [Keep a Changelog](https://keepachangelog.com/)
conventions and [Semantic Versioning](https://semver.org/).

## [Unreleased]
### Added
- `Module/ExtractWatershedPourpoint.py`: pourpoint-based vector watershed
  delineation on the TDX-Hydro HFX S3 dataset (CSV batch + `--test` mode),
  credentials via AWS profile `pourpoint-hfx`.
- Upstream river-network GPKG per dam, built from the dataset's native
  `stems` snap layer filtered to the watershed's upstream unit IDs.
- `<name>_watershed_merged.gpkg` / `<name>_river_network_merged.gpkg`: all per-dam
  GPKGs combined (with `Dam_ID`), rebuilt at the end of every run.
- `--csv` non-interactive mode; reruns now keep earlier diagnostics and refill
  `Area_km2` for already-processed dams.
- Overwrite mode for reruns: `--overwrite` flag, or a Yes/No prompt in dialog mode
  when results already exist; recomputes every dam and removes stale per-dam files.
- Delineation now runs through pourpoint's staged API; the pre-merge sub-basins
  are saved per dam (`<name>_subbasins_pourpoint/<Dam_ID>_SubBasins.gpkg`, plus a
  merged file) before `dissolve()` produces the watershed.
- Documentation updated (script docstring, README, RUN_COMMANDS, CLAUDE.md) for the
  staged-API sub-basin output, merged files, `--csv`/`--overwrite` and run-from-project-folder note.
- Closest-feature (`distance-first`) outlet snapping.
- mnema memory scaffolding: per-project store at `Resources/.mnema`, plus
  `doctrine` and `library` read-only vaults. See `CLAUDE.md` → "Memory
  (mnema)" and `RUN_COMMANDS.md` → "Memory (mnema)".

## [0.1.0] - YYYY-MM-DD
### Added
- Initial version.
