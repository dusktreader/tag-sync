"""Project-level configuration for tag-sync.

Config is loaded from the project directory and may live in any one of these
locations (mutually exclusive — having more than one is an error):

- `.tag-sync.toml`
- `.tag-sync.json`
- `.tag-sync.yaml` or `.tag-sync.yml`
- `pyproject.toml` under `[tool.tag-sync]`
- `package.json` under the `"tag-sync"` key
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from tag_sync.exceptions import TagSyncError


class TagSyncConfig(BaseModel):
    """Configuration for tag-sync loaded from a project config source."""

    model_config = ConfigDict(extra="forbid")

    tag_pattern: str | None = None


@dataclass
class _ConfigSource:
    """A discovered config source: the file it came from and the raw data dict."""

    label: str
    data: dict


def _load_toml_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("rb") as f:
        return tomllib.load(f)


def _load_json_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open() as f:
        return json.load(f)


def _load_yaml_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open() as f:
        return yaml.safe_load(f)


def _collect_sources(directory: Path) -> list[_ConfigSource]:
    """Return all config sources found in `directory`. May be empty or more than one."""
    sources: list[_ConfigSource] = []

    # Standalone .tag-sync.toml
    data = _load_toml_file(directory / ".tag-sync.toml")
    if data is not None:
        sources.append(_ConfigSource(label=".tag-sync.toml", data=data))

    # Standalone .tag-sync.json
    data = _load_json_file(directory / ".tag-sync.json")
    if data is not None:
        sources.append(_ConfigSource(label=".tag-sync.json", data=data))

    # Standalone .tag-sync.yaml / .tag-sync.yml
    for name in (".tag-sync.yaml", ".tag-sync.yml"):
        data = _load_yaml_file(directory / name)
        if data is not None:
            sources.append(_ConfigSource(label=name, data=data))
            break  # only count once even if both exist (rare)

    # pyproject.toml [tool.tag-sync]
    pyproject = _load_toml_file(directory / "pyproject.toml")
    if pyproject is not None:
        nested = pyproject.get("tool", {}).get("tag-sync")
        if nested is not None:
            sources.append(_ConfigSource(label="pyproject.toml [tool.tag-sync]", data=nested))

    # package.json ["tag-sync"]
    package_json = _load_json_file(directory / "package.json")
    if package_json is not None:
        nested = package_json.get("tag-sync")
        if nested is not None:
            sources.append(_ConfigSource(label='package.json ["tag-sync"]', data=nested))

    return sources


def load_config(directory: Path) -> TagSyncConfig | None:
    """
    Load tag-sync configuration from the given project directory.

    Returns `None` if no config is found.  Raises `TagSyncError` if config is
    present in more than one location, or if a config source contains
    unrecognized keys.
    """
    sources = _collect_sources(directory)

    if len(sources) > 1:
        labels = ", ".join(s.label for s in sources)
        raise TagSyncError(
            f"tag-sync configuration found in multiple places: {labels}. "
            "Provide configuration in exactly one location."
        )

    if not sources:
        return None

    source = sources[0]
    try:
        return TagSyncConfig.model_validate(source.data)
    except Exception as exc:
        raise TagSyncError(
            f"Invalid tag-sync configuration in {source.label}: {exc}"
        ) from exc
