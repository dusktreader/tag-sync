# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v0.2.0 - 2026-05-01

### Added

- `--tag-pattern` option on all four commands
  - overrides the default `v{version}` format with any `{version}`-bearing pattern
  - e.g. `release/qastg/{version}` produces `release/qastg/1.2.3`
- Config file support for `tag-pattern`
  - accepted locations:
    - `pyproject.toml [tool.tag-sync]`
    - `package.json ["tag-sync"]`
    - `.tag-sync.toml`
    - `.tag-sync.json`
    - `.tag-sync.yaml`/`.yml`,
  - multiple config sources in the same directory are an error
  - unknown keys are rejected immediately
- `Tagger.from_tag_pattern()`, `Tagger.from_version_string()`, and `Tagger.from_tag_string()` classmethods
- `TagSyncConfig` Pydantic model with strict unknown-key rejection
- `pyyaml>=6.0` as a declared dependency
- PEP 440 version parsing for Python projects via `packaging.version.Version`
  - two-part versions (`1.2`) are accepted; patch defaults to 0
  - pre-release forms `a`, `b`, `rc`, and `.dev` are all handled
  - post-release versions (`1.2.3.post1`) raise a clear error


### Changed

- All explicit version arguments now accept either a bare semver (`1.2.3`) or the full tag string (`v1.2.3`)
  - bare semver is tried first; the configured tag pattern is applied either way
  - applies to `check`, `publish`, and `nuke`


### Fixed

- `version.py` fallback paths marked `# pragma: no cover`
  - keeps the 100% coverage threshold passing when the package is not installed from metadata


## v0.1.1 - 2026-04-09

### Added

- Support for python 3.12


## v0.1.0 - 2026-04-03

### Added

- Initial release of `tag-sync`
- `verify` command — reports whether the current package version has a published git tag on origin
- `check` command — validates that a given version matches the current package version
- `publish` command — derives or validates a tag, creates it locally, and pushes it to origin
  - `--replace` to overwrite an existing tag after confirmation
  - `--dry-run` to preview without making changes
- `nuke` command — deletes a tag from both the local repository and origin
  - `--force` to skip the confirmation prompt
  - `--dry-run` to preview without making changes
- Auto-detection of packager from project directory
  - `pyproject.toml` → `uv`
  - `package.json` → `npm`
- `--packager` option to override auto-detection on all commands
- `--directory` / `-d` option to target a project outside the current working directory
- SemVer parsing and formatting via configurable `Pattern` templates with pre-release support
- GitHub Actions workflows for CI/QA, documentation deployment, and tag-triggered PyPI publishing
- MkDocs-based documentation covering quickstart, features, and publishing guides
