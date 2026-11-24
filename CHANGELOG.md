# Changelog

<!-- markdownlint-configure-file { "MD024": { "siblings_only": true } } -->

This file lists the changes to the starter in each release. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The version numbers
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). The version
is in `pyproject.toml`. Each SYSTEM session adds its changes here before it
ends. [The system guide](guidance/starter/system.md) gives the procedure.

## [Unreleased]

## [0.3.0] - 2026-11-24

### Added

- Use `setup.py --resource ID` to cache HTML, plain text and source code.
  The local reference index links to the saved file and any Wayback copy.

## [0.2.1] - 2026-11-17

### Fixed

- Automated checks and snapshots now use VICE console mode. Only interactive runs open an emulator window.

## [0.2.0] - 2026-11-16

This is the first release. The git history has the changes before it.

### Added

- SYSTEM mode, for changes to the starter itself. It starts only when the
  owner asks for it by name. Read `guidance/starter/system.md`.
- `scripts/release.py`: makes sure that the version in `pyproject.toml`,
  `uv.lock` and this file is the same, and prints the notes of a release.

### Changed

- A lab answers programming questions only. It does not add abilities to
  `scripts/c64.py`. Changes to tools are SYSTEM work.
