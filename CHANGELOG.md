# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


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
