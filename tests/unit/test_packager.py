"""Tests for tag_sync.packager — Packager, UvPackager, NpmPackager, PACKAGERS, detect_packager, resolve_packager."""

from pathlib import Path

import pytest

from tag_sync.exceptions import TagSyncError, VersionParseError
from tag_sync.packager import PACKAGERS, NpmPackager, Packager, UvPackager, detect_packager, resolve_packager
from tag_sync.pattern import Pattern
from tag_sync.semver import SemVer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def uv_pattern() -> Pattern:
    return Pattern(
        "<major>.<minor>.<patch><pre_type:a|b|rc|dev><pre_id>",
        pretype_map={"a": "alpha", "b": "beta"},
    )


@pytest.fixture
def concrete_packager(uv_pattern: Pattern) -> Packager:
    """A minimal concrete Packager subclass for testing the base class behaviour."""

    class _TestPackager(Packager):
        def __init__(self) -> None:
            self.pattern = uv_pattern

        def extract_version_string(self) -> str:
            raise NotImplementedError

    return _TestPackager()


# ---------------------------------------------------------------------------
# Packager (abstract base)
# ---------------------------------------------------------------------------


class TestPackager:
    def test_parse_delegates_to_pattern(self, concrete_packager: Packager) -> None:
        assert concrete_packager.parse("1.2.3") == SemVer(1, 2, 3)

    def test_parse_prerelease_maps_to_canonical(self, concrete_packager: Packager) -> None:
        assert concrete_packager.parse("2.0.0a1") == SemVer(2, 0, 0, "alpha", 1)

    def test_format_delegates_to_pattern(self, concrete_packager: Packager) -> None:
        assert concrete_packager.format(SemVer(2, 0, 0, "alpha", 1)) == "2.0.0a1"

    def test_cannot_instantiate_without_implementing_abstract_method(self) -> None:
        class _Incomplete(Packager):
            pass

        with pytest.raises(TypeError):
            _Incomplete()  # type: ignore[abstract]

    def test_package_version_wraps_not_implemented_as_version_parse_error(self, concrete_packager: Packager) -> None:
        with pytest.raises(VersionParseError):
            _ = concrete_packager.package_version


# ---------------------------------------------------------------------------
# UvPackager
# ---------------------------------------------------------------------------


class TestUvPackager:
    def test_pattern_template(self) -> None:
        assert UvPackager().pattern.template == "<major>.<minor>.<patch><pre_type:a|b|rc|dev><pre_id>"

    def test_pretype_map_a_to_alpha(self) -> None:
        assert UvPackager().pattern.pretype_map["a"] == "alpha"

    def test_pretype_map_b_to_beta(self) -> None:
        assert UvPackager().pattern.pretype_map["b"] == "beta"

    def test_pretype_map_rc_identity(self) -> None:
        assert UvPackager().pattern.pretype_map["rc"] == "rc"

    def test_pretype_map_dev_identity(self) -> None:
        assert UvPackager().pattern.pretype_map["dev"] == "dev"

    def test_parse_alpha_maps_to_canonical(self) -> None:
        assert UvPackager().parse("2.0.0a1") == SemVer(2, 0, 0, "alpha", 1)

    def test_format_canonical_back_to_short(self) -> None:
        assert UvPackager().format(SemVer(2, 0, 0, "alpha", 1)) == "2.0.0a1"

    def test_extract_version_string_reads_pyproject(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.2.3"\n')
        assert UvPackager(tmp_path).extract_version_string() == "1.2.3"

    def test_accepts_path_argument(self, tmp_path: Path) -> None:
        assert UvPackager(tmp_path).path == tmp_path

    def test_default_path_is_cwd(self) -> None:
        assert UvPackager().path == Path(".")


# ---------------------------------------------------------------------------
# NpmPackager
# ---------------------------------------------------------------------------


class TestNpmPackager:
    def test_pattern_template(self) -> None:
        assert NpmPackager().pattern.template == "<major>.<minor>.<patch>-<pre_type:alpha|beta|rc|dev>.<pre_id>"

    def test_no_pretype_map(self) -> None:
        assert NpmPackager().pattern.pretype_map == {"alpha": "alpha", "beta": "beta", "rc": "rc", "dev": "dev"}

    def test_parse_alpha(self) -> None:
        assert NpmPackager().parse("2.0.0-alpha.1") == SemVer(2, 0, 0, "alpha", 1)

    def test_format_alpha(self) -> None:
        assert NpmPackager().format(SemVer(2, 0, 0, "alpha", 1)) == "2.0.0-alpha.1"

    def test_extract_version_string_reads_package_json(self, tmp_path: Path) -> None:
        package_json = tmp_path / "package.json"
        package_json.write_text('{"version": "1.2.3"}')
        assert NpmPackager(tmp_path).extract_version_string() == "1.2.3"

    def test_accepts_path_argument(self, tmp_path: Path) -> None:
        assert NpmPackager(tmp_path).path == tmp_path

    def test_default_path_is_cwd(self) -> None:
        assert NpmPackager().path == Path(".")


# ---------------------------------------------------------------------------
# PACKAGERS registry
# ---------------------------------------------------------------------------


class TestPackagersRegistry:
    def test_npm_key_maps_to_npm_packager(self) -> None:
        assert PACKAGERS["npm"] is NpmPackager

    def test_npm_instantiates_correctly(self) -> None:
        assert isinstance(PACKAGERS["npm"](), NpmPackager)

    def test_uv_key_maps_to_uv_packager(self) -> None:
        assert PACKAGERS["uv"] is UvPackager

    def test_uv_instantiates_correctly(self) -> None:
        assert isinstance(PACKAGERS["uv"](), UvPackager)


# ---------------------------------------------------------------------------
# detect_packager
# ---------------------------------------------------------------------------


class TestDetectPackager:
    def test_detects_uv_from_pyproject_toml(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n')
        packager = detect_packager(tmp_path)
        assert isinstance(packager, UvPackager)
        assert packager.path == tmp_path

    def test_detects_npm_from_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"version": "1.0.0"}')
        packager = detect_packager(tmp_path)
        assert isinstance(packager, NpmPackager)
        assert packager.path == tmp_path

    def test_raises_when_no_manifest_found(self, tmp_path: Path) -> None:
        with pytest.raises(TagSyncError, match="No supported manifest file found"):
            detect_packager(tmp_path)

    def test_raises_when_both_manifests_present(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n')
        (tmp_path / "package.json").write_text('{"version": "1.0.0"}')
        with pytest.raises(TagSyncError, match="Multiple manifest files found"):
            detect_packager(tmp_path)

    def test_error_message_includes_directory_path(self, tmp_path: Path) -> None:
        with pytest.raises(TagSyncError, match=str(tmp_path)):
            detect_packager(tmp_path)


# ---------------------------------------------------------------------------
# resolve_packager
# ---------------------------------------------------------------------------


class TestResolvePackager:
    def test_none_name_delegates_to_detect_packager(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n')
        packager = resolve_packager(None, tmp_path)
        assert isinstance(packager, UvPackager)

    def test_explicit_name_returns_named_packager(self, tmp_path: Path) -> None:
        packager = resolve_packager("npm", tmp_path)
        assert isinstance(packager, NpmPackager)
        assert packager.path == tmp_path

    def test_explicit_name_overrides_manifest_on_disk(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n')
        packager = resolve_packager("npm", tmp_path)
        assert isinstance(packager, NpmPackager)

    def test_path_is_forwarded_to_packager(self, tmp_path: Path) -> None:
        packager = resolve_packager("uv", tmp_path)
        assert isinstance(packager, UvPackager)
        assert packager.path == tmp_path
