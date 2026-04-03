# Features


## Packager auto-detection

`tag-sync` inspects the target directory for known manifest files and selects
the right packager automatically:

| Manifest file    | Packager |
|------------------|----------|
| `pyproject.toml` | `uv`     |
| `package.json`   | `npm`    |

If neither or both manifest files are present, `tag-sync` raises an error and
asks you to pass `--packager` explicitly.

Use `--packager` to override auto-detection at any time:

```bash
tag-sync verify --packager uv
tag-sync verify --packager npm
```


## Directory targeting

All commands accept `--directory` / `-d` so you can operate on any project
without changing your working directory:

```bash
tag-sync publish -d ~/projects/my-lib
```

The directory is passed to the packager for manifest lookup and used as the
working directory for all git operations.


## Tag pattern

Tags are formatted as `v<major>.<minor>.<patch>` by default (e.g. `v1.2.3`).
The pattern is derived from the package version using SemVer parsing, so
non-standard version strings are caught early with a clear error.


## Verify Publication

Reports whether the tag derived from the current package version is already
published on origin.  No git state is modified.

```bash
tag-sync verify
```


## Check that a tag matches

Validates that an explicit tag string matches the current package version.
Useful as a pre-publish sanity check in CI or a Makefile.

```bash
tag-sync check v1.2.3
```

Exits with a non-zero code if the tag does not match.


## Publish a new tag matching the project version

Creates a git tag and pushes it to origin.

```bash
# Derive tag from package version (no version-match check)
tag-sync publish

# Supply tag explicitly (validates against package version first)
tag-sync publish v1.2.3
```


### Already-published guard

`tag-sync publish` always checks that the tag is not already on origin before
pushing.  If it is, the command fails with a clear message.


### --replace

Pass `--replace` to overwrite an existing tag.  You will be prompted to
confirm; the old tag is deleted locally and on origin before the new one is
created.  If `--replace` is given but the tag is not yet published, the flag is
silently ignored and the normal publish flow runs.

```bash
tag-sync publish --replace
```


### --dry-run

Print what would happen without making any changes to local or remote state:

```bash
tag-sync publish --dry-run
```

----

## nuke

Deletes a tag from both the local repository and origin.  Prompts for
confirmation by default.

```bash
tag-sync nuke v1.2.3

# Skip the prompt
tag-sync nuke v1.2.3 --force
```

```bash
tag-sync nuke v1.2.3 --dry-run
```
