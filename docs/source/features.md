# Features


## Packager auto-detection

`tag-sync` inspects the target directory for known manifest files and selects
the right packager automatically:

| Manifest file    | Packager | Version format |
|------------------|----------|----------------|
| `pyproject.toml` | `uv`     | PEP 440        |
| `package.json`   | `npm`    | SemVer         |

If neither or both manifest files are present, `tag-sync` raises an error and
asks you to pass `--packager` explicitly.

Use `--packager` to override auto-detection at any time:

```bash
tag-sync verify --packager uv
tag-sync verify --packager npm
```


## Version format support

### Python projects (uv / pyproject.toml)

Version strings are parsed with `packaging.version.Version`, so any PEP 440
string is accepted:

| Version string   | Parsed as                  |
|------------------|----------------------------|
| `1.2.3`          | release                    |
| `1.2`            | release (patch defaults to 0) |
| `2.0.0a1`        | alpha pre-release          |
| `1.2.3b2`        | beta pre-release           |
| `1.0.0rc1`       | release candidate          |
| `1.0.0.dev3`     | dev release                |

Post-release versions (`1.2.3.post1`) are not supported and raise an error.

### npm projects (package.json)

Version strings follow standard SemVer (`1.2.3`), with optional pre-release
segments in the form `1.2.3-alpha.1`, `1.2.3-beta.2`, `1.2.3-rc.1`.
Two-part versions are not valid npm versions and are not accepted.


## Directory targeting

All commands accept `--directory` / `-d` so you can operate on any project
without changing your working directory:

```bash
tag-sync publish -d ~/projects/my-lib
```

The directory is used for manifest lookup, config file discovery, and as the
working directory for all git operations.


## Tag pattern and configuration

Every command that takes an explicit version accepts either a bare semver
(e.g. `1.2.3`) or the full tag name (e.g. `v1.2.3`). A separate tag pattern
controls what the full git tag name looks like.

The default pattern is `v{version}`, which produces tags like `v1.2.3`. The
`{version}` placeholder is always substituted with the bare semver.

To use a different pattern, pass `--tag-pattern` on the command line:

```bash
tag-sync publish --tag-pattern "release/qastg/{version}"
# creates the tag: release/qastg/1.2.3

tag-sync verify  --tag-pattern "release/qastg/{version}"
tag-sync check   1.2.3 --tag-pattern "release/qastg/{version}"
tag-sync nuke    1.2.3 --tag-pattern "release/qastg/{version}" --force
# full tag name works too:
tag-sync check   release/qastg/1.2.3 --tag-pattern "release/qastg/{version}"
tag-sync nuke    release/qastg/1.2.3 --tag-pattern "release/qastg/{version}" --force
```

### Project config file

Repeating `--tag-pattern` on every command is tedious. Put it in a project
config file instead. `tag-sync` looks for configuration in the following
locations (exactly one must be present or none at all — having more than one
is an error):

| Location | Format |
|----------|--------|
| `.tag-sync.toml` | TOML |
| `.tag-sync.json` | JSON |
| `.tag-sync.yaml` / `.tag-sync.yml` | YAML |
| `pyproject.toml` under `[tool.tag-sync]` | TOML (embedded) |
| `package.json` under `"tag-sync"` key | JSON (embedded) |

Example — standalone TOML:

```toml
# .tag-sync.toml
tag_pattern = "release/qastg/{version}"
```

Example — embedded in `pyproject.toml`:

```toml
[tool.tag-sync]
tag_pattern = "release/qastg/{version}"
```

Example — embedded in `package.json`:

```json
{
  "name": "my-package",
  "version": "1.2.3",
  "tag-sync": {
    "tag_pattern": "release/qastg/{version}"
  }
}
```

With any of these in place, all commands pick up the pattern automatically and
`--tag-pattern` can be omitted:

```bash
tag-sync verify
tag-sync check 1.2.3
tag-sync publish
tag-sync nuke 1.2.3 --force
```

`--tag-pattern` on the command line always overrides the config file, so you
can use the config for the common case and override it for one-off runs.

Any unrecognized key in the config raises an error immediately rather than
silently being ignored.


## Verify publication

Reports whether the tag for the current package version is already published
on origin. No git state is modified.

```bash
tag-sync verify
```


## Check that a version matches

Validates that the given version matches the current package version. Useful as a
pre-publish sanity check in CI or a Makefile.

```bash
tag-sync check 1.2.3
# or pass the full tag name:
tag-sync check v1.2.3
```

The argument is a bare semver or the full tag name — both work. Bare semver is
tried first; if it doesn't parse, the configured pattern is used to parse the
full tag name.

Exits with a non-zero code if the version does not match.


## Publish a new tag matching the project version

Creates a git tag and pushes it to origin.

```bash
# Derive tag from package version (no version-match check)
tag-sync publish

# Supply version explicitly (validates against package version first)
tag-sync publish 1.2.3
# or pass the full tag name:
tag-sync publish v1.2.3
```


### Already-published guard

`tag-sync publish` always checks that the tag is not already on origin before
pushing. If it is, the command fails with a clear message.


### --replace

Pass `--replace` to overwrite an existing tag. You will be prompted to confirm;
the old tag is deleted locally and on origin before the new one is created. If
`--replace` is given but the tag is not yet published, the flag is silently
ignored and the normal publish flow runs.

```bash
tag-sync publish --replace
```


### --dry-run

Print what would happen without making any changes to local or remote state:

```bash
tag-sync publish --dry-run
```

---

## nuke

Deletes a tag from both the local repository and origin. Prompts for
confirmation by default.

```bash
tag-sync nuke 1.2.3
# or pass the full tag name:
tag-sync nuke v1.2.3

# Skip the prompt
tag-sync nuke 1.2.3 --force
```

```bash
tag-sync nuke 1.2.3 --dry-run
```
