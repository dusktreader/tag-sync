"""Tests for tag_sync.pattern — Pattern construction, parsing, and formatting."""

import pytest

from tag_sync.exceptions import InvalidPatternError, VersionParseError
from tag_sync.pattern import Pattern
from tag_sync.semver import SemVer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tagger_pattern() -> Pattern:
    return Pattern("v<major>.<minor>.<patch>-<pre_type:alpha|beta|rc|dev>.<pre_id>")


@pytest.fixture
def uv_pattern() -> Pattern:
    return Pattern(
        "<major>.<minor>.<patch><pre_type:a|b|rc|dev><pre_id>",
        pretype_map={"a": "alpha", "b": "beta"},
    )


# ---------------------------------------------------------------------------
# Pattern construction
# ---------------------------------------------------------------------------


class TestPatternConstruction:
    def test_valid_template_stored(self, tagger_pattern: Pattern) -> None:
        assert tagger_pattern.template == "v<major>.<minor>.<patch>-<pre_type:alpha|beta|rc|dev>.<pre_id>"

    def test_invalid_template_raises(self) -> None:
        with pytest.raises(InvalidPatternError):
            Pattern("not-a-valid-template")

    def test_pretype_map_explicit_entries(self, uv_pattern: Pattern) -> None:
        assert uv_pattern.pretype_map["a"] == "alpha"
        assert uv_pattern.pretype_map["b"] == "beta"

    def test_pretype_map_identity_supplement_rc(self, uv_pattern: Pattern) -> None:
        assert uv_pattern.pretype_map["rc"] == "rc"

    def test_pretype_map_identity_supplement_dev(self, uv_pattern: Pattern) -> None:
        assert uv_pattern.pretype_map["dev"] == "dev"

    def test_identity_pretype_map_when_no_map_given(self, tagger_pattern: Pattern) -> None:
        for key in ("alpha", "beta", "rc", "dev"):
            assert tagger_pattern.pretype_map[key] == key

    def test_no_pretype_map_arg_builds_full_identity_map(self) -> None:
        p = Pattern("<major>.<minor>.<patch><pre_type:alpha|beta|rc|dev><pre_id>")
        assert set(p.pretype_map.keys()) == {"alpha", "beta", "rc", "dev"}


# ---------------------------------------------------------------------------
# Pattern.format
# ---------------------------------------------------------------------------


class TestPatternFormat:
    def test_tagger_release(self, tagger_pattern: Pattern) -> None:
        assert tagger_pattern.format(SemVer(1, 2, 3)) == "v1.2.3"

    def test_tagger_alpha(self, tagger_pattern: Pattern) -> None:
        assert tagger_pattern.format(SemVer(2, 0, 0, "alpha", 1)) == "v2.0.0-alpha.1"

    def test_tagger_rc(self, tagger_pattern: Pattern) -> None:
        assert tagger_pattern.format(SemVer(3, 0, 0, "rc", 2)) == "v3.0.0-rc.2"

    def test_uv_release(self, uv_pattern: Pattern) -> None:
        assert uv_pattern.format(SemVer(1, 2, 3)) == "1.2.3"

    def test_uv_alpha_canonical_to_short(self, uv_pattern: Pattern) -> None:
        assert uv_pattern.format(SemVer(2, 0, 0, "alpha", 1)) == "2.0.0a1"

    def test_uv_beta_canonical_to_short(self, uv_pattern: Pattern) -> None:
        assert uv_pattern.format(SemVer(1, 5, 2, "beta", 3)) == "1.5.2b3"

    def test_uv_rc_passthrough(self, uv_pattern: Pattern) -> None:
        assert uv_pattern.format(SemVer(3, 0, 0, "rc", 2)) == "3.0.0rc2"

    def test_no_pre_when_pre_type_none(self, tagger_pattern: Pattern) -> None:
        result = tagger_pattern.format(SemVer(1, 0, 0, pre_type=None, pre_id=None))
        assert result == "v1.0.0"


# ---------------------------------------------------------------------------
# Pattern.parse — tagger pattern (identity pretype_map)
# ---------------------------------------------------------------------------


class TestPatternParseTaggerPattern:
    def test_release(self, tagger_pattern: Pattern) -> None:
        assert tagger_pattern.parse("v1.2.3") == SemVer(1, 2, 3)

    def test_alpha(self, tagger_pattern: Pattern) -> None:
        assert tagger_pattern.parse("v2.0.0-alpha.1") == SemVer(2, 0, 0, "alpha", 1)

    def test_beta(self, tagger_pattern: Pattern) -> None:
        assert tagger_pattern.parse("v1.5.2-beta.3") == SemVer(1, 5, 2, "beta", 3)

    def test_rc(self, tagger_pattern: Pattern) -> None:
        assert tagger_pattern.parse("v3.0.0-rc.2") == SemVer(3, 0, 0, "rc", 2)

    def test_dev(self, tagger_pattern: Pattern) -> None:
        assert tagger_pattern.parse("v0.1.0-dev.7") == SemVer(0, 1, 0, "dev", 7)

    def test_missing_prefix_raises(self, tagger_pattern: Pattern) -> None:
        with pytest.raises(VersionParseError):
            tagger_pattern.parse("1.2.3")

    def test_garbage_raises(self, tagger_pattern: Pattern) -> None:
        with pytest.raises(VersionParseError):
            tagger_pattern.parse("not-a-version")


# ---------------------------------------------------------------------------
# Pattern.parse — uv pattern (pretype_map maps raw -> canonical)
# ---------------------------------------------------------------------------


class TestPatternParseUvPattern:
    def test_release(self, uv_pattern: Pattern) -> None:
        assert uv_pattern.parse("1.2.3") == SemVer(1, 2, 3)

    def test_alpha_maps_to_canonical(self, uv_pattern: Pattern) -> None:
        assert uv_pattern.parse("2.0.0a1") == SemVer(2, 0, 0, "alpha", 1)

    def test_beta_maps_to_canonical(self, uv_pattern: Pattern) -> None:
        assert uv_pattern.parse("1.5.2b3") == SemVer(1, 5, 2, "beta", 3)

    def test_rc_passthrough(self, uv_pattern: Pattern) -> None:
        assert uv_pattern.parse("3.0.0rc2") == SemVer(3, 0, 0, "rc", 2)

    def test_dev_passthrough(self, uv_pattern: Pattern) -> None:
        assert uv_pattern.parse("0.1.0dev7") == SemVer(0, 1, 0, "dev", 7)

    def test_unexpected_prefix_raises(self, uv_pattern: Pattern) -> None:
        with pytest.raises(VersionParseError):
            uv_pattern.parse("v1.2.3")

    def test_garbage_raises(self, uv_pattern: Pattern) -> None:
        with pytest.raises(VersionParseError):
            uv_pattern.parse("not-a-version")


# ---------------------------------------------------------------------------
# Cross-pattern version equality
# ---------------------------------------------------------------------------


class TestCrossPatternVersionEquality:
    def test_stable_versions_equal(self, tagger_pattern: Pattern, uv_pattern: Pattern) -> None:
        assert tagger_pattern.parse("v1.2.3") == uv_pattern.parse("1.2.3")

    def test_prerelease_equal_after_canonical_mapping(self, tagger_pattern: Pattern, uv_pattern: Pattern) -> None:
        assert tagger_pattern.parse("v2.0.0-alpha.1") == uv_pattern.parse("2.0.0a1")

    def test_different_versions_not_equal(self, tagger_pattern: Pattern, uv_pattern: Pattern) -> None:
        assert tagger_pattern.parse("v1.0.0") != uv_pattern.parse("2.0.0")
