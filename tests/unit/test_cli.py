"""Tests for tag_sync CLI commands — verify, check, publish, nuke."""

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from tag_sync.cli.main import cli
from tag_sync.exceptions import GitError, TagAlreadyPublishedError, TagSyncError, VersionMismatchError
from tag_sync.packager import UvPackager
from tag_sync.semver import SemVer
from tag_sync.tagger import Tagger

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def mock_tagger(version_string: str = "v1.0.0") -> MagicMock:
    """Return a MagicMock shaped like a Tagger for the given version string."""
    real = Tagger(version_string)
    tagger = MagicMock(spec=Tagger)
    tagger.pattern = real.pattern
    tagger.version = real.version
    return tagger


def mock_packager(version: SemVer = SemVer(1, 0, 0)) -> MagicMock:
    """Return a MagicMock shaped like a UvPackager."""
    real = UvPackager()
    packager = MagicMock(spec=UvPackager)
    packager.pattern = real.pattern
    packager.package_version = version
    packager.format.side_effect = real.pattern.format
    return packager


@contextmanager
def patch_packagers(packager: MagicMock):
    """
    Patch resolve_packager so that any packager resolution returns the given
    mock packager regardless of name or auto-detection.
    """
    with patch("tag_sync.cli.main.resolve_packager", return_value=packager):
        yield


# ---------------------------------------------------------------------------
# verify (checks whether the current package version has been published)
# ---------------------------------------------------------------------------


class TestVerify:
    @contextmanager
    def _patch_verify(self, packager: MagicMock, tagger: MagicMock):
        """Patch for verify: Tagger constructor + DEFAULT_PATTERN_TEMPLATE class attr."""
        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger) as mock_tagger_cls:
            mock_tagger_cls.DEFAULT_PATTERN_TEMPLATE = Tagger.DEFAULT_PATTERN_TEMPLATE
            yield mock_tagger_cls

    def test_published(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("v1.0.0")
        tagger.is_published.return_value = True

        with self._patch_verify(packager, tagger):
            result = runner.invoke(cli, ["verify"])

        assert result.exit_code == 0
        assert "already published" in result.output

    def test_not_published(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("v1.0.0")
        tagger.is_published.return_value = False

        with self._patch_verify(packager, tagger):
            result = runner.invoke(cli, ["verify"])

        assert result.exit_code == 0
        assert "not been published" in result.output

    def test_version_string_appears_in_output(self) -> None:
        packager = mock_packager(SemVer(2, 3, 4))
        tagger = mock_tagger("v2.3.4")
        tagger.is_published.return_value = True

        with self._patch_verify(packager, tagger):
            result = runner.invoke(cli, ["verify"])

        assert "v2.3.4" in result.output

    def test_explicit_packager_option(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("v1.0.0")
        tagger.is_published.return_value = True

        with self._patch_verify(packager, tagger):
            result = runner.invoke(cli, ["verify", "--packager", "uv"])

        assert result.exit_code == 0

    def test_auto_detect_used_when_no_packager_given(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("v1.0.0")
        tagger.is_published.return_value = True

        with self._patch_verify(packager, tagger):
            with patch("tag_sync.cli.main.resolve_packager", return_value=packager) as mock_resolve:
                result = runner.invoke(cli, ["verify"])

        assert result.exit_code == 0
        mock_resolve.assert_called_once()

    def test_directory_option_passed_to_resolve_packager(self, tmp_path: Path) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("v1.0.0")
        tagger.is_published.return_value = True

        with self._patch_verify(packager, tagger):
            with patch("tag_sync.cli.main.resolve_packager", return_value=packager) as mock_resolve:
                result = runner.invoke(cli, ["verify", "--directory", str(tmp_path)])

        assert result.exit_code == 0
        mock_resolve.assert_called_once_with(None, tmp_path)

    def test_detect_error_propagates(self) -> None:
        with patch("tag_sync.cli.main.resolve_packager", side_effect=TagSyncError("no manifest")):
            result = runner.invoke(cli, ["verify"])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# check (validates a tag version against the current package version)
# ---------------------------------------------------------------------------


class TestCheck:
    def test_matching_version_succeeds(self) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v1.0.0")
        tagger.check.return_value = None

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["check", "v1.0.0"])

        assert result.exit_code == 0
        assert "matches the package version" in result.output
        tagger.check.assert_called_once_with(packager)

    def test_mismatched_version_fails(self) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v2.0.0")
        tagger.check.side_effect = VersionMismatchError("version mismatch")

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["check", "v2.0.0"])

        assert result.exit_code != 0

    def test_version_string_appears_in_output(self) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v3.1.4")
        tagger.check.return_value = None

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["check", "v3.1.4"])

        assert "v3.1.4" in result.output

    def test_directory_option_passed_to_resolve_packager(self, tmp_path: Path) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v1.0.0")
        tagger.check.return_value = None

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            with patch("tag_sync.cli.main.resolve_packager", return_value=packager) as mock_resolve:
                result = runner.invoke(cli, ["check", "--directory", str(tmp_path), "v1.0.0"])

        assert result.exit_code == 0
        mock_resolve.assert_called_once_with(None, tmp_path)


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------


class TestPublish:
    def test_success(self) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v1.0.0")

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["publish", "v1.0.0"])

        assert result.exit_code == 0
        assert "published successfully" in result.output
        tagger.check.assert_called_once_with(packager)
        tagger.make_tag.assert_called_once_with(dry_run=False)
        tagger.push_tag.assert_called_once_with(dry_run=False)

    def test_explicit_packager_option(self) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v1.0.0")

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["publish", "--packager", "uv", "v1.0.0"])

        assert result.exit_code == 0
        tagger.check.assert_called_once_with(packager)

    def test_dry_run(self) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v1.0.0")

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["publish", "--dry-run", "v1.0.0"])

        assert result.exit_code == 0
        tagger.make_tag.assert_called_once_with(dry_run=True)
        tagger.push_tag.assert_called_once_with(dry_run=True)

    def test_replace_confirmed_deletes_then_publishes(self) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v1.0.0")
        tagger.require_unpublished.side_effect = TagAlreadyPublishedError("already published")

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["publish", "--replace", "v1.0.0"], input="y\n")

        assert result.exit_code == 0
        tagger.delete_local_tag.assert_called_once_with(dry_run=False)
        tagger.delete_remote_tag.assert_called_once_with(dry_run=False)
        tagger.make_tag.assert_called_once()
        tagger.push_tag.assert_called_once()

    def test_replace_declined_skips_delete(self) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v1.0.0")
        tagger.require_unpublished.side_effect = TagAlreadyPublishedError("already published")

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["publish", "--replace", "v1.0.0"], input="n\n")

        assert result.exit_code != 0
        tagger.delete_local_tag.assert_not_called()
        tagger.delete_remote_tag.assert_not_called()
        tagger.make_tag.assert_not_called()

    def test_replace_not_published_skips_prompt_and_delete(self) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v1.0.0")
        # require_unpublished does NOT raise — tag is not yet on origin

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["publish", "--replace", "v1.0.0"])

        assert result.exit_code == 0
        tagger.delete_local_tag.assert_not_called()
        tagger.delete_remote_tag.assert_not_called()
        tagger.make_tag.assert_called_once()
        tagger.push_tag.assert_called_once()

    def test_already_published_fails(self) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v1.0.0")
        tagger.require_unpublished.side_effect = TagAlreadyPublishedError("already published")

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["publish", "v1.0.0"])

        assert result.exit_code != 0
        tagger.make_tag.assert_not_called()
        tagger.push_tag.assert_not_called()

    def test_already_published_with_replace_succeeds(self) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v1.0.0")
        tagger.require_unpublished.side_effect = TagAlreadyPublishedError("already published")

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["publish", "--replace", "v1.0.0"], input="y\n")

        assert result.exit_code == 0
        tagger.require_unpublished.assert_called_once()
        tagger.delete_local_tag.assert_called_once_with(dry_run=False)
        tagger.delete_remote_tag.assert_called_once_with(dry_run=False)
        tagger.make_tag.assert_called_once()
        tagger.push_tag.assert_called_once()

    def test_omitted_tag_skips_check(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("v1.0.0")

        with (
            patch_packagers(packager),
            patch("tag_sync.cli.main.Tagger", return_value=tagger) as mock_tagger_cls,
        ):
            mock_tagger_cls.DEFAULT_PATTERN_TEMPLATE = Tagger.DEFAULT_PATTERN_TEMPLATE
            result = runner.invoke(cli, ["publish"])

        assert result.exit_code == 0
        tagger.check.assert_not_called()

    def test_check_failure_aborts_before_tag(self) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v1.0.0")
        tagger.check.side_effect = VersionMismatchError("mismatch")

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["publish", "v1.0.0"])

        assert result.exit_code != 0
        tagger.make_tag.assert_not_called()
        tagger.push_tag.assert_not_called()

    def test_git_error_on_make_tag_fails(self) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v1.0.0")
        tagger.make_tag.side_effect = GitError("tag already exists")

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["publish", "v1.0.0"])

        assert result.exit_code != 0
        tagger.push_tag.assert_not_called()

    def test_directory_option_passed_to_resolve_packager(self, tmp_path: Path) -> None:
        packager = mock_packager()
        tagger = mock_tagger("v1.0.0")

        with patch_packagers(packager), patch("tag_sync.cli.main.Tagger", return_value=tagger):
            with patch("tag_sync.cli.main.resolve_packager", return_value=packager) as mock_resolve:
                result = runner.invoke(cli, ["publish", "--directory", str(tmp_path), "v1.0.0"])

        assert result.exit_code == 0
        mock_resolve.assert_called_once_with(None, tmp_path)

    def test_omitted_tag_derived_from_packager_version(self) -> None:
        packager = mock_packager(SemVer(2, 3, 4))
        tagger = mock_tagger("v2.3.4")

        with (
            patch_packagers(packager),
            patch("tag_sync.cli.main.Tagger", return_value=tagger) as mock_tagger_cls,
        ):
            mock_tagger_cls.DEFAULT_PATTERN_TEMPLATE = Tagger.DEFAULT_PATTERN_TEMPLATE
            result = runner.invoke(cli, ["publish"])

        assert result.exit_code == 0
        mock_tagger_cls.assert_called_once_with("v2.3.4")

    def test_omitted_tag_prerelease_derived_correctly(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0, "alpha", 1))
        tagger = mock_tagger("v1.0.0-alpha.1")

        with (
            patch_packagers(packager),
            patch("tag_sync.cli.main.Tagger", return_value=tagger) as mock_tagger_cls,
        ):
            mock_tagger_cls.DEFAULT_PATTERN_TEMPLATE = Tagger.DEFAULT_PATTERN_TEMPLATE
            result = runner.invoke(cli, ["publish"])

        assert result.exit_code == 0
        mock_tagger_cls.assert_called_once_with("v1.0.0-alpha.1")


# ---------------------------------------------------------------------------
# nuke
# ---------------------------------------------------------------------------


class TestNuke:
    def test_confirmed_via_prompt(self) -> None:
        tagger = mock_tagger("v1.0.0")

        with patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["nuke", "v1.0.0"], input="y\n")

        assert result.exit_code == 0
        assert "removed locally" in result.output
        tagger.delete_local_tag.assert_called_once_with(dry_run=False)
        tagger.delete_remote_tag.assert_called_once_with(dry_run=False)

    def test_declined_via_prompt_aborts(self) -> None:
        tagger = mock_tagger("v1.0.0")

        with patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["nuke", "v1.0.0"], input="n\n")

        assert result.exit_code != 0
        tagger.delete_local_tag.assert_not_called()
        tagger.delete_remote_tag.assert_not_called()

    def test_force_skips_prompt(self) -> None:
        tagger = mock_tagger("v1.0.0")

        with patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["nuke", "--force", "v1.0.0"])

        assert result.exit_code == 0
        tagger.delete_local_tag.assert_called_once_with(dry_run=False)
        tagger.delete_remote_tag.assert_called_once_with(dry_run=False)

    def test_dry_run(self) -> None:
        tagger = mock_tagger("v1.0.0")

        with patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["nuke", "--force", "--dry-run", "v1.0.0"])

        assert result.exit_code == 0
        tagger.delete_local_tag.assert_called_once_with(dry_run=True)
        tagger.delete_remote_tag.assert_called_once_with(dry_run=True)

    def test_version_string_appears_in_output(self) -> None:
        tagger = mock_tagger("v2.0.0-alpha.1")

        with patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["nuke", "--force", "v2.0.0-alpha.1"])

        assert "v2.0.0-alpha.1" in result.output

    def test_git_error_on_delete_local_fails(self) -> None:
        tagger = mock_tagger("v1.0.0")
        tagger.delete_local_tag.side_effect = GitError("tag not found")

        with patch("tag_sync.cli.main.Tagger", return_value=tagger):
            result = runner.invoke(cli, ["nuke", "--force", "v1.0.0"])

        assert result.exit_code != 0
        tagger.delete_remote_tag.assert_not_called()
