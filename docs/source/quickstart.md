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


### Validate that a tag matches the current version

```bash
tag-sync check v1.2.3
```

Confirms that `v1.2.3` matches the version in your manifest. A tag argument is
always required.


### Publish with an explicit tag (with version validation)

```bash
tag-sync publish v1.2.3
```

When a tag is supplied explicitly, `tag-sync` validates it against the manifest
version before publishing.


### Replace an already-published tag

```bash
tag-sync publish --replace
```

If the tag already exists on origin you will be prompted to confirm before the
old tag is deleted and the new one is pushed.


### Remove a tag everywhere

```bash
tag-sync nuke v1.2.3
```

Deletes the tag from both the local repository and origin.  You will be
prompted to confirm unless `--force` is passed.


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
