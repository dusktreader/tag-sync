# Quickstart


## Requirements

- Python 3.13+
- A project that uses `pyproject.toml` or `package.json` that includes version info.
- A git repository with a remote named `origin`


## Installation

Install from PyPI via pip or uv:

```bash
pip install tag-sync
```

```bash
uv add tag-sync
```


## Basic workflow

### Check whether your current version is already tagged

```bash
tag-sync verify
```

`tag-sync` auto-detects your packager and reports whether the current version
has a published tag on origin.


### Publish a tag for the current version

```bash
tag-sync publish
```

This derives the tag from the package version, confirms the tag is not already
on origin, creates it locally, and pushes it.


### Validate that a version matches your project

```bash
tag-sync check 1.2.3
```

Confirms that `1.2.3` matches the version in your manifest. The argument is always the
bare semver — no `v` prefix or path components.


### Publish with an explicit version (with version validation)

```bash
tag-sync publish 1.2.3
```

When a version is supplied explicitly, `tag-sync` validates it against the
manifest version before publishing.


### Replace an already-published tag

```bash
tag-sync publish --replace
```

If the tag already exists on origin you will be prompted to confirm before the
old tag is deleted and the new one is pushed.


### Remove a tag everywhere

```bash
tag-sync nuke 1.2.3
```

Deletes the tag from both the local repository and origin. You will be prompted
to confirm unless `--force` is passed.


## Using a custom tag pattern

By default `tag-sync` creates tags in `v{version}` form (e.g. `v1.2.3`). If
your project uses a different convention, pass `--tag-pattern`:

```bash
tag-sync publish --tag-pattern "release/qastg/{version}"
tag-sync verify  --tag-pattern "release/qastg/{version}"
tag-sync check   1.2.3 --tag-pattern "release/qastg/{version}"
tag-sync nuke    1.2.3 --tag-pattern "release/qastg/{version}" --force
```

`{version}` is the bare semver (e.g. `1.2.3`), so `publish` and `verify` produce
tags like `release/qastg/1.2.3`, and `check` and `nuke` accept the bare semver and derive the full tag name.

To avoid repeating `--tag-pattern` on every command, put it in a config file
instead. See the [tag pattern and configuration](features.md#tag-pattern-and-configuration)
section of the features page.


## Targeting a different directory

All commands accept `--directory` / `-d` to point at a project outside the
current working directory:

```bash
tag-sync verify -d ~/projects/my-lib
tag-sync publish -d ~/projects/my-lib
```


## Specifying the packager explicitly

If your project root contains both `pyproject.toml` and `package.json`,
auto-detection will raise an error and ask you to be explicit:

```bash
tag-sync verify --packager uv
tag-sync verify --packager npm
```
