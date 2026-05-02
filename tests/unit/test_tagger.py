"""Tests for tag_sync.tagger — Tagger construction and git operations."""

from unittest.mock import MagicMock, patch

import pytest

from tag_sync.exceptions import GitError, TagAlreadyPublishedError, VersionMismatchError, VersionParseError
from tag_sync.packager import Packager, UvPackager
from tag_sync.tagger import DEFAULT_TAG_PATTERN, Tagger
from tag_sync.semver import SemVer


# ---------------------------------------------------------------------------
# Tagger construction
# ---------------------------------------------------------------------------


class TestTaggerConstruction:
    def test_default_pattern_template(self) -> None:
        assert Tagger("v1.2.3").pattern.template == Tagger.DEFAULT_PATTERN_TEMPLATE

    def test_parses_release(self) -> None:
        assert Tagger("v1.2.3").version == SemVer(1, 2, 3)

    def test_parses_alpha(self) -> None:
        assert Tagger("v2.0.0-alpha.1").version == SemVer(2, 0, 0, "alpha", 1)

    def test_parses_beta(self) -> None:
        assert Tagger("v1.5.2-beta.3").version == SemVer(1, 5, 2, "beta", 3)

    def test_parses_rc(self) -> None:
        assert Tagger("v3.0.0-rc.2").version == SemVer(3, 0, 0, "rc", 2)

    def test_invalid_raises(self) -> None:
        with pytest.raises(VersionParseError):
            Tagger("1.2.3")


# ---------------------------------------------------------------------------
# Tagger.from_tag_pattern
# ---------------------------------------------------------------------------


class TestTaggerFromTagPattern:
    def test_default_tag_pattern_constant_is_v_version(self) -> None:
        assert DEFAULT_TAG_PATTERN == "v{version}"

    def test_default_tag_pattern_produces_v_prefix(self) -> None:
        tagger = Tagger.from_tag_pattern(SemVer(1, 2, 3))
        assert tagger.pattern.format(tagger.version) == "v1.2.3"

    def test_custom_prefix_template(self) -> None:
        tagger = Tagger.from_tag_pattern(SemVer(1, 2, 3), "release/qastg/{version}")
        assert tagger.pattern.format(tagger.version) == "release/qastg/1.2.3"

    def test_custom_prefix_template_no_v(self) -> None:
        tagger = Tagger.from_tag_pattern(SemVer(1, 2, 3), "release/qastg/{version}")
        tag = tagger.pattern.format(tagger.version)
        assert tag == "release/qastg/1.2.3"
        assert not tag.startswith("v")

    def test_prerelease_version(self) -> None:
        tagger = Tagger.from_tag_pattern(SemVer(2, 0, 0, "alpha", 1), "release/{version}")
        assert tagger.pattern.format(tagger.version) == "release/2.0.0-alpha.1"

    def test_version_is_correctly_parsed(self) -> None:
        tagger = Tagger.from_tag_pattern(SemVer(3, 4, 5), "deploy/{version}")
        assert tagger.version == SemVer(3, 4, 5)

    def test_prerelease_version_is_correctly_parsed(self) -> None:
        tagger = Tagger.from_tag_pattern(SemVer(1, 0, 0, "beta", 2), "release/{version}")
        assert tagger.version == SemVer(1, 0, 0, "beta", 2)

    def test_git_ops_use_full_tag(self) -> None:
        tagger = Tagger.from_tag_pattern(SemVer(1, 2, 3), "release/qastg/{version}")
        mock_repo = MagicMock()
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            tagger.make_tag()
        mock_repo.create_tag.assert_called_once_with("release/qastg/1.2.3")

    def test_is_published_uses_full_tag(self) -> None:
        tagger = Tagger.from_tag_pattern(SemVer(1, 2, 3), "release/qastg/{version}")
        mock_repo = MagicMock()
        mock_repo.git.ls_remote.return_value = ""
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            tagger.is_published()
        mock_repo.git.ls_remote.assert_called_once_with("--tags", "origin", "release/qastg/1.2.3")

    def test_push_tag_uses_full_tag(self) -> None:
        tagger = Tagger.from_tag_pattern(SemVer(1, 2, 3), "release/qastg/{version}")
        mock_repo = MagicMock()
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            tagger.push_tag()
        mock_repo.remotes["origin"].push.assert_called_once_with("release/qastg/1.2.3")

    def test_delete_remote_tag_uses_full_tag(self) -> None:
        tagger = Tagger.from_tag_pattern(SemVer(1, 2, 3), "release/qastg/{version}")
        mock_repo = MagicMock()
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            tagger.delete_remote_tag()
        mock_repo.remotes["origin"].push.assert_called_once_with(
            refspec=":refs/tags/release/qastg/1.2.3"
        )

    def test_require_unpublished_error_includes_full_tag(self) -> None:
        tagger = Tagger.from_tag_pattern(SemVer(1, 2, 3), "release/qastg/{version}")
        mock_repo = MagicMock()
        mock_repo.git.ls_remote.return_value = "abc123\trefs/tags/release/qastg/1.2.3\n"
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            with pytest.raises(TagAlreadyPublishedError, match="release/qastg/1.2.3"):
                tagger.require_unpublished()


# ---------------------------------------------------------------------------
# Tagger.from_version_string
# ---------------------------------------------------------------------------


class TestTaggerFromVersionString:
    def test_default_pattern_produces_v_prefix(self) -> None:
        tagger = Tagger.from_version_string("1.2.3")
        assert tagger.version == SemVer(1, 2, 3)
        assert tagger.pattern.format(tagger.version) == "v1.2.3"

    def test_custom_pattern_produces_full_tag(self) -> None:
        tagger = Tagger.from_version_string("1.2.3", "release/qastg/{version}")
        assert tagger.version == SemVer(1, 2, 3)
        assert tagger.pattern.format(tagger.version) == "release/qastg/1.2.3"

    def test_prerelease_version(self) -> None:
        tagger = Tagger.from_version_string("2.0.0-alpha.1", "release/{version}")
        assert tagger.version == SemVer(2, 0, 0, "alpha", 1)
        assert tagger.pattern.format(tagger.version) == "release/2.0.0-alpha.1"

    def test_roundtrip_with_from_tag_pattern(self) -> None:
        semver = SemVer(3, 4, 5)
        tag_pattern = "deploy/{version}"
        tagger_a = Tagger.from_tag_pattern(semver, tag_pattern)
        tagger_b = Tagger.from_version_string("3.4.5", tag_pattern)
        assert tagger_b.version == tagger_a.version
        assert tagger_b.pattern.format(tagger_b.version) == tagger_a.pattern.format(tagger_a.version)


# ---------------------------------------------------------------------------
# Tagger.from_tag_string
# ---------------------------------------------------------------------------


class TestTaggerFromTagString:
    def test_default_pattern_parses_v_prefixed_tag(self) -> None:
        tagger = Tagger.from_tag_string("v1.2.3")
        assert tagger.version == SemVer(1, 2, 3)
        assert tagger.pattern.format(tagger.version) == "v1.2.3"

    def test_custom_pattern_strips_prefix(self) -> None:
        tagger = Tagger.from_tag_string("release/qastg/1.2.3", "release/qastg/{version}")
        assert tagger.version == SemVer(1, 2, 3)
        assert tagger.pattern.format(tagger.version) == "release/qastg/1.2.3"

    def test_prerelease(self) -> None:
        tagger = Tagger.from_tag_string("release/2.0.0-alpha.1", "release/{version}")
        assert tagger.version == SemVer(2, 0, 0, "alpha", 1)

    def test_roundtrip_with_from_tag_pattern(self) -> None:
        semver = SemVer(3, 4, 5)
        tag_pattern = "deploy/{version}"
        tagger_a = Tagger.from_tag_pattern(semver, tag_pattern)
        full_tag = tagger_a.pattern.format(tagger_a.version)
        tagger_b = Tagger.from_tag_string(full_tag, tag_pattern)
        assert tagger_b.version == semver
        assert tagger_b.pattern.format(tagger_b.version) == full_tag


# ---------------------------------------------------------------------------
# Tagger.from_version_or_tag_string
# ---------------------------------------------------------------------------


class TestTaggerFromVersionOrTagString:
    def test_bare_semver_default_pattern(self) -> None:
        tagger = Tagger.from_version_or_tag_string("1.2.3")
        assert tagger.version == SemVer(1, 2, 3)
        assert tagger.pattern.format(tagger.version) == "v1.2.3"

    def test_full_tag_default_pattern(self) -> None:
        tagger = Tagger.from_version_or_tag_string("v1.2.3")
        assert tagger.version == SemVer(1, 2, 3)
        assert tagger.pattern.format(tagger.version) == "v1.2.3"

    def test_full_tag_custom_pattern(self) -> None:
        tagger = Tagger.from_version_or_tag_string("release/qastg/1.2.3", "release/qastg/{version}")
        assert tagger.version == SemVer(1, 2, 3)
        assert tagger.pattern.format(tagger.version) == "release/qastg/1.2.3"

    def test_bare_semver_custom_pattern(self) -> None:
        tagger = Tagger.from_version_or_tag_string("1.2.3", "release/qastg/{version}")
        assert tagger.version == SemVer(1, 2, 3)
        assert tagger.pattern.format(tagger.version) == "release/qastg/1.2.3"

    def test_prerelease_bare_semver(self) -> None:
        tagger = Tagger.from_version_or_tag_string("2.0.0-alpha.1")
        assert tagger.version == SemVer(2, 0, 0, "alpha", 1)
        assert tagger.pattern.format(tagger.version) == "v2.0.0-alpha.1"

    def test_prerelease_full_tag(self) -> None:
        tagger = Tagger.from_version_or_tag_string("v2.0.0-alpha.1")
        assert tagger.version == SemVer(2, 0, 0, "alpha", 1)
        assert tagger.pattern.format(tagger.version) == "v2.0.0-alpha.1"

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(Exception):
            Tagger.from_version_or_tag_string("not-a-version")


# ---------------------------------------------------------------------------
# Tagger.check
# ---------------------------------------------------------------------------


class TestTaggerCheck:
    def test_matching_release_passes(self) -> None:
        tagger = Tagger("v1.2.3")
        packager = MagicMock(spec=Packager)
        packager.package_version = SemVer(1, 2, 3)
        packager.pattern = tagger.pattern
        tagger.check(packager)  # no exception

    def test_matching_prerelease_passes(self) -> None:
        tagger = Tagger("v2.0.0-alpha.1")
        packager = MagicMock(spec=Packager)
        packager.package_version = SemVer(2, 0, 0, "alpha", 1)
        packager.pattern = tagger.pattern
        tagger.check(packager)  # no exception

    def test_mismatched_version_raises(self) -> None:
        tagger = Tagger("v1.2.3")
        packager = MagicMock(spec=Packager)
        packager.package_version = SemVer(2, 0, 0)
        packager.pattern = tagger.pattern
        with pytest.raises(VersionMismatchError):
            tagger.check(packager)

    def test_mismatched_pre_type_raises(self) -> None:
        tagger = Tagger("v1.0.0-alpha.1")
        packager = MagicMock(spec=Packager)
        packager.package_version = SemVer(1, 0, 0, "beta", 1)
        packager.pattern = tagger.pattern
        with pytest.raises(VersionMismatchError):
            tagger.check(packager)

    def test_error_message_uses_packager_pattern_for_package_version(self) -> None:
        tagger = Tagger("v1.2.3")
        packager = MagicMock(spec=Packager)
        packager.package_version = SemVer(2, 0, 0)
        packager.pattern = UvPackager().pattern
        with pytest.raises(VersionMismatchError, match="2.0.0"):
            tagger.check(packager)


# ---------------------------------------------------------------------------
# Tagger.is_published
# ---------------------------------------------------------------------------


class TestTaggerIsPublished:
    def test_returns_true_when_remote_has_tag(self) -> None:
        tagger = Tagger("v1.0.0")
        mock_repo = MagicMock()
        mock_repo.git.ls_remote.return_value = "abc123\trefs/tags/v1.0.0\n"
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            assert tagger.is_published() is True

    def test_returns_false_when_remote_lacks_tag(self) -> None:
        tagger = Tagger("v1.0.0")
        mock_repo = MagicMock()
        mock_repo.git.ls_remote.return_value = ""
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            assert tagger.is_published() is False

    def test_calls_ls_remote_with_correct_args(self) -> None:
        tagger = Tagger("v1.2.3")
        mock_repo = MagicMock()
        mock_repo.git.ls_remote.return_value = ""
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            tagger.is_published()
        mock_repo.git.ls_remote.assert_called_once_with("--tags", "origin", "v1.2.3")


# ---------------------------------------------------------------------------
# Tagger.require_unpublished
# ---------------------------------------------------------------------------


class TestTaggerRequireUnpublished:
    def test_passes_when_tag_not_published(self) -> None:
        tagger = Tagger("v1.0.0")
        mock_repo = MagicMock()
        mock_repo.git.ls_remote.return_value = ""
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            tagger.require_unpublished()  # no exception

    def test_raises_when_tag_already_published(self) -> None:
        tagger = Tagger("v1.0.0")
        mock_repo = MagicMock()
        mock_repo.git.ls_remote.return_value = "abc123\trefs/tags/v1.0.0\n"
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            with pytest.raises(TagAlreadyPublishedError):
                tagger.require_unpublished()

    def test_error_message_includes_tag_and_replace_hint(self) -> None:
        tagger = Tagger("v2.0.0-alpha.1")
        mock_repo = MagicMock()
        mock_repo.git.ls_remote.return_value = "abc123\trefs/tags/v2.0.0-alpha.1\n"
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            with pytest.raises(TagAlreadyPublishedError, match="v2.0.0-alpha.1"):
                tagger.require_unpublished()
            with pytest.raises(TagAlreadyPublishedError, match="--replace"):
                tagger.require_unpublished()


# ---------------------------------------------------------------------------
# Tagger.make_tag
# ---------------------------------------------------------------------------


class TestTaggerMakeTag:
    def test_creates_tag_via_repo(self) -> None:
        tagger = Tagger("v1.0.0")
        mock_repo = MagicMock()
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            tagger.make_tag()
        mock_repo.create_tag.assert_called_once_with("v1.0.0")

    def test_dry_run_skips_repo(self) -> None:
        tagger = Tagger("v1.0.0")
        with patch("tag_sync.tagger.Repo") as mock_repo_cls:
            tagger.make_tag(dry_run=True)
        mock_repo_cls.assert_not_called()

    def test_failure_raises_git_error(self) -> None:
        tagger = Tagger("v1.0.0")
        mock_repo = MagicMock()
        mock_repo.create_tag.side_effect = Exception("tag already exists")
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            with pytest.raises(GitError):
                tagger.make_tag()


# ---------------------------------------------------------------------------
# Tagger.push_tag
# ---------------------------------------------------------------------------


class TestTaggerPushTag:
    def test_pushes_tag_to_origin(self) -> None:
        tagger = Tagger("v1.0.0")
        mock_repo = MagicMock()
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            tagger.push_tag()
        mock_repo.remotes["origin"].push.assert_called_once_with("v1.0.0")

    def test_dry_run_skips_repo(self) -> None:
        tagger = Tagger("v1.0.0")
        with patch("tag_sync.tagger.Repo") as mock_repo_cls:
            tagger.push_tag(dry_run=True)
        mock_repo_cls.assert_not_called()

    def test_failure_raises_git_error(self) -> None:
        tagger = Tagger("v1.0.0")
        mock_repo = MagicMock()
        mock_repo.remotes["origin"].push.side_effect = Exception("remote error")
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            with pytest.raises(GitError):
                tagger.push_tag()


# ---------------------------------------------------------------------------
# Tagger.delete_local_tag
# ---------------------------------------------------------------------------


class TestTaggerDeleteLocalTag:
    def test_deletes_tag_via_repo(self) -> None:
        tagger = Tagger("v1.0.0")
        mock_repo = MagicMock()
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            tagger.delete_local_tag()
        mock_repo.delete_tag.assert_called_once()

    def test_dry_run_skips_repo(self) -> None:
        tagger = Tagger("v1.0.0")
        with patch("tag_sync.tagger.Repo") as mock_repo_cls:
            tagger.delete_local_tag(dry_run=True)
        mock_repo_cls.assert_not_called()

    def test_failure_raises_git_error(self) -> None:
        tagger = Tagger("v1.0.0")
        mock_repo = MagicMock()
        mock_repo.delete_tag.side_effect = Exception("tag not found")
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            with pytest.raises(GitError):
                tagger.delete_local_tag()


# ---------------------------------------------------------------------------
# Tagger.delete_remote_tag
# ---------------------------------------------------------------------------


class TestTaggerDeleteRemoteTag:
    def test_pushes_delete_refspec_to_origin(self) -> None:
        tagger = Tagger("v1.0.0")
        mock_repo = MagicMock()
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            tagger.delete_remote_tag()
        mock_repo.remotes["origin"].push.assert_called_once_with(refspec=":refs/tags/v1.0.0")

    def test_dry_run_skips_repo(self) -> None:
        tagger = Tagger("v1.0.0")
        with patch("tag_sync.tagger.Repo") as mock_repo_cls:
            tagger.delete_remote_tag(dry_run=True)
        mock_repo_cls.assert_not_called()

    def test_failure_raises_git_error(self) -> None:
        tagger = Tagger("v1.0.0")
        mock_repo = MagicMock()
        mock_repo.remotes["origin"].push.side_effect = Exception("remote error")
        with patch("tag_sync.tagger.Repo", return_value=mock_repo):
            with pytest.raises(GitError):
                tagger.delete_remote_tag()
