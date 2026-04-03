"""Tests for tag_sync.semver — SemVer construction and equality."""

from tag_sync.semver import SemVer


# ---------------------------------------------------------------------------
# SemVer construction and equality
# ---------------------------------------------------------------------------


class TestSemVerConstruction:
    def test_release_fields(self) -> None:
        v = SemVer(major=1, minor=2, patch=3)
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.pre_type is None
        assert v.pre_id is None

    def test_prerelease_fields(self) -> None:
        v = SemVer(major=2, minor=0, patch=0, pre_type="alpha", pre_id=1)
        assert v.pre_type == "alpha"
        assert v.pre_id == 1

    def test_equality_release(self) -> None:
        assert SemVer(1, 2, 3) == SemVer(1, 2, 3)

    def test_equality_prerelease(self) -> None:
        assert SemVer(1, 2, 3, "alpha", 1) == SemVer(1, 2, 3, "alpha", 1)

    def test_inequality_different_patch(self) -> None:
        assert SemVer(1, 2, 3) != SemVer(1, 2, 4)

    def test_inequality_different_pre_type(self) -> None:
        assert SemVer(1, 0, 0, "alpha", 1) != SemVer(1, 0, 0, "beta", 1)

    def test_inequality_release_vs_prerelease(self) -> None:
        assert SemVer(1, 0, 0) != SemVer(1, 0, 0, "alpha", 1)

    def test_equality_with_non_semver_returns_not_implemented(self) -> None:
        assert SemVer(1, 2, 3).__eq__("1.2.3") is NotImplemented

    def test_hash_equal_semvers_match(self) -> None:
        assert hash(SemVer(1, 2, 3)) == hash(SemVer(1, 2, 3))

    def test_usable_as_set_member(self) -> None:
        s = {SemVer(1, 2, 3), SemVer(1, 2, 3), SemVer(2, 0, 0)}
        assert len(s) == 2
