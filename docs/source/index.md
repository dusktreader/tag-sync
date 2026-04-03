# Home

![tag-sync icon](images/tag-sync-icon.png){ width=300 }

_A CLI tool for syncing git tags with project versions._


## Overview

`tag-sync` keeps your git tags in step with your project's package version.
It reads the current version from your project manifest (`pyproject.toml` for
Python projects, `package.json` for npm projects), converts it to a
canonical tag string, and pushes the new tag to origin. It also provides
commands to verify, validate, publish, and remove tags. These are all wrapped
up into a nice CLI.

Key capabilities:

- **Auto-detect** the packager from the project directory
- **Verify** whether the current package version already has a published tag
- **Check** that an explicit tag string matches the current package version
- **Publish** a new tag derived from (or validated against) the package version
- **Nuke** a tag from both local and origin when you need to clean up


## Why tag-sync?

Manually keeping git tags aligned with `version = "x.y.z"` in your manifest is
error-prone: you might forget to push the tag, push the wrong version, or end
up with a published tag that doesn't match the package on PyPI.  `tag-sync`
makes the manifest the single source of truth and enforces that contract at
publish time.
