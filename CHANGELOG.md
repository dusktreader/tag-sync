# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v0.2.0 - 2026-05-01

### Added

- `--tag-pattern` option on all four commands — override the default `v{version}` tag format with any `{version}`-bearing pattern (e.g. `release/qastg/{version}`)
- Config file support — `tag-pattern` can be set in `.tag-sync.toml`, `.tag-sync.json`, `.tag-sync.yaml`/`.yml`, `pyproject.toml [tool.tag-sync]`, or `package.json ["tag-sync"]`; multiple config sources in the same directory are an error (finally, a reason to actually read the error message)
- `Tagger.from_tag_pattern()`, `Tagger.from_version_string()`, and `Tagger.from_tag_string()` classmethods for constructing taggers from bare semver strings and custom patterns
- `TagSyncConfig` Pydantic model with strict unknown-key rejection
- `pyyaml>=6.0` as a declared dependency

### Changed

- All CLI version arguments are now bare semver (e.g. `1.2.3`); the full git tag name is derived from the active tag pattern
- `check` and `nuke` commands accept bare semver and derive the tag, consistent with `publish`

### Fixed

- `version.py` fallback paths marked `# pragma: no cover` so 100% coverage threshold holds when the package is not installed from metadata


## v0.1.1 - 2026-04-09

### Added

- Support for python 3.12


## v0.1.0 - 2026-04-03

### Added

- Initial release of `tag-sync`
- `verify` command — reports whether the current package version has a published git tag on origin
- `check` command — validates that an explicit tag string matches the current package version
- `publish` command — derives or validates a tag, creates it locally, and pushes it to origin; supports `--replace` and `--dry-run`
- `nuke` command — deletes a tag from both the local repository and origin; supports `--force` and `--dry-run`
- Auto-detection of packager from project directory (`pyproject.toml` → `uv`, `package.json` → `npm`)
- `--packager` option to override auto-detection on all commands
- `--directory` / `-d` option to target a project outside the current working directory
- SemVer parsing and formatting via configurable `Pattern` templates with pre-release support
- GitHub Actions workflows for CI/QA, documentation deployment, and tag-triggered PyPI publishing
- MkDocs-based documentation covering quickstart, features, and publishing guides
