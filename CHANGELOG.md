# Changelog

All notable changes to a project derived from this template should be
recorded here, following [Keep a Changelog](https://keepachangelog.com/)
conventions and [Semantic Versioning](https://semver.org/).

## [Unreleased]
### Added
- `Module/ExtractWatershedPourpoint.py`: pourpoint-based vector watershed
  delineation on the TDX-Hydro HFX S3 dataset (CSV batch + `--test` mode),
  credentials via AWS profile `pourpoint-hfx`.
- mnema memory scaffolding: per-project store at `Resources/.mnema`, plus
  `doctrine` and `library` read-only vaults. See `CLAUDE.md` → "Memory
  (mnema)" and `RUN_COMMANDS.md` → "Memory (mnema)".

## [0.1.0] - YYYY-MM-DD
### Added
- Initial version.
