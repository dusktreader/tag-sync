"""Tests for tag_sync.config — TagSyncConfig and load_config."""

import json
from pathlib import Path

import pytest

from tag_sync.config import TagSyncConfig, load_config
from tag_sync.exceptions import TagSyncError


PATTERN = "release/qastg/{version}"


# ---------------------------------------------------------------------------
# TagSyncConfig model
# ---------------------------------------------------------------------------


class TestTagSyncConfig:
    def test_default_tag_pattern_is_none(self) -> None:
        config = TagSyncConfig()
        assert config.tag_pattern is None

    def test_tag_pattern_is_stored(self) -> None:
        config = TagSyncConfig(tag_pattern=PATTERN)
        assert config.tag_pattern == PATTERN

    def test_unknown_key_raises(self) -> None:
        with pytest.raises(Exception):
            TagSyncConfig.model_validate({"unknown_key": "value"})

    def test_valid_dict_parses(self) -> None:
        config = TagSyncConfig.model_validate({"tag_pattern": PATTERN})
        assert config.tag_pattern == PATTERN

    def test_empty_dict_parses(self) -> None:
        config = TagSyncConfig.model_validate({})
        assert config.tag_pattern is None


# ---------------------------------------------------------------------------
# load_config — no config present
# ---------------------------------------------------------------------------


class TestLoadConfigAbsent:
    def test_returns_none_when_no_config(self, tmp_path: Path) -> None:
        assert load_config(tmp_path) is None

    def test_ignores_unrelated_files(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "foo"\nversion = "1.0.0"\n')
        (tmp_path / "package.json").write_text('{"name": "foo", "version": "1.0.0"}\n')
        assert load_config(tmp_path) is None


# ---------------------------------------------------------------------------
# load_config — standalone files
# ---------------------------------------------------------------------------


class TestLoadConfigToml:
    def test_loads_tag_sync_toml(self, tmp_path: Path) -> None:
        (tmp_path / ".tag-sync.toml").write_text(f'tag_pattern = "{PATTERN}"\n')
        config = load_config(tmp_path)
        assert config is not None
        assert config.tag_pattern == PATTERN

    def test_empty_toml_returns_defaults(self, tmp_path: Path) -> None:
        (tmp_path / ".tag-sync.toml").write_text("")
        config = load_config(tmp_path)
        assert config is not None
        assert config.tag_pattern is None

    def test_unknown_key_in_toml_raises(self, tmp_path: Path) -> None:
        (tmp_path / ".tag-sync.toml").write_text('unknown = "oops"\n')
        with pytest.raises(TagSyncError, match=".tag-sync.toml"):
            load_config(tmp_path)


class TestLoadConfigJson:
    def test_loads_tag_sync_json(self, tmp_path: Path) -> None:
        (tmp_path / ".tag-sync.json").write_text(json.dumps({"tag_pattern": PATTERN}))
        config = load_config(tmp_path)
        assert config is not None
        assert config.tag_pattern == PATTERN

    def test_empty_json_object_returns_defaults(self, tmp_path: Path) -> None:
        (tmp_path / ".tag-sync.json").write_text("{}")
        config = load_config(tmp_path)
        assert config is not None
        assert config.tag_pattern is None

    def test_unknown_key_in_json_raises(self, tmp_path: Path) -> None:
        (tmp_path / ".tag-sync.json").write_text(json.dumps({"unknown": "oops"}))
        with pytest.raises(TagSyncError, match=".tag-sync.json"):
            load_config(tmp_path)


class TestLoadConfigYaml:
    def test_loads_tag_sync_yaml(self, tmp_path: Path) -> None:
        (tmp_path / ".tag-sync.yaml").write_text(f"tag_pattern: '{PATTERN}'\n")
        config = load_config(tmp_path)
        assert config is not None
        assert config.tag_pattern == PATTERN

    def test_loads_tag_sync_yml(self, tmp_path: Path) -> None:
        (tmp_path / ".tag-sync.yml").write_text(f"tag_pattern: '{PATTERN}'\n")
        config = load_config(tmp_path)
        assert config is not None
        assert config.tag_pattern == PATTERN

    def test_unknown_key_in_yaml_raises(self, tmp_path: Path) -> None:
        (tmp_path / ".tag-sync.yaml").write_text("unknown: oops\n")
        with pytest.raises(TagSyncError, match=".tag-sync.yaml"):
            load_config(tmp_path)


# ---------------------------------------------------------------------------
# load_config — embedded in pyproject.toml
# ---------------------------------------------------------------------------


class TestLoadConfigPyproject:
    def test_loads_tool_tag_sync_section(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            f'[project]\nname = "foo"\n\n[tool.tag-sync]\ntag_pattern = "{PATTERN}"\n'
        )
        config = load_config(tmp_path)
        assert config is not None
        assert config.tag_pattern == PATTERN

    def test_pyproject_without_tool_tag_sync_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "foo"\n')
        assert load_config(tmp_path) is None

    def test_unknown_key_in_pyproject_section_raises(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[tool.tag-sync]\nunknown = "oops"\n')
        with pytest.raises(TagSyncError, match="pyproject.toml"):
            load_config(tmp_path)


# ---------------------------------------------------------------------------
# load_config — embedded in package.json
# ---------------------------------------------------------------------------


class TestLoadConfigPackageJson:
    def test_loads_tag_sync_key(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "foo", "version": "1.0.0", "tag-sync": {"tag_pattern": PATTERN}})
        )
        config = load_config(tmp_path)
        assert config is not None
        assert config.tag_pattern == PATTERN

    def test_package_json_without_tag_sync_key_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "foo"}\n')
        assert load_config(tmp_path) is None

    def test_unknown_key_in_package_json_section_raises(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"tag-sync": {"unknown": "oops"}}))
        with pytest.raises(TagSyncError, match="package.json"):
            load_config(tmp_path)


# ---------------------------------------------------------------------------
# load_config — conflict detection
# ---------------------------------------------------------------------------


class TestLoadConfigConflict:
    def test_two_standalone_files_raises(self, tmp_path: Path) -> None:
        (tmp_path / ".tag-sync.toml").write_text(f'tag_pattern = "{PATTERN}"\n')
        (tmp_path / ".tag-sync.json").write_text(json.dumps({"tag_pattern": PATTERN}))
        with pytest.raises(TagSyncError, match="multiple places"):
            load_config(tmp_path)

    def test_standalone_and_pyproject_raises(self, tmp_path: Path) -> None:
        (tmp_path / ".tag-sync.toml").write_text(f'tag_pattern = "{PATTERN}"\n')
        (tmp_path / "pyproject.toml").write_text(f'[tool.tag-sync]\ntag_pattern = "{PATTERN}"\n')
        with pytest.raises(TagSyncError, match="multiple places"):
            load_config(tmp_path)

    def test_standalone_and_package_json_raises(self, tmp_path: Path) -> None:
        (tmp_path / ".tag-sync.json").write_text(json.dumps({"tag_pattern": PATTERN}))
        (tmp_path / "package.json").write_text(json.dumps({"tag-sync": {"tag_pattern": PATTERN}}))
        with pytest.raises(TagSyncError, match="multiple places"):
            load_config(tmp_path)

    def test_pyproject_and_package_json_raises(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(f'[tool.tag-sync]\ntag_pattern = "{PATTERN}"\n')
        (tmp_path / "package.json").write_text(json.dumps({"tag-sync": {"tag_pattern": PATTERN}}))
        with pytest.raises(TagSyncError, match="multiple places"):
            load_config(tmp_path)

    def test_error_message_names_all_conflicting_sources(self, tmp_path: Path) -> None:
        (tmp_path / ".tag-sync.toml").write_text(f'tag_pattern = "{PATTERN}"\n')
        (tmp_path / ".tag-sync.json").write_text(json.dumps({"tag_pattern": PATTERN}))
        with pytest.raises(TagSyncError) as exc_info:
            load_config(tmp_path)
        msg = str(exc_info.value)
        assert ".tag-sync.toml" in msg
        assert ".tag-sync.json" in msg
