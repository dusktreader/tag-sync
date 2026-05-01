"""Tests for tag_sync CLI commands — verify, check, publish, nuke."""

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from tag_sync.cli.main import cli
from tag_sync.config import TagSyncConfig
from tag_sync.exceptions import GitError, TagAlreadyPublishedError, TagSyncError, VersionMismatchError
from tag_sync.packager import UvPackager
from tag_sync.semver import SemVer
from tag_sync.tagger import DEFAULT_TAG_PATTERN, Tagger

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def mock_tagger(version_string: str = "1.0.0") -> MagicMock:
    """
    Return a MagicMock shaped like a Tagger built from from_version_string.

    Uses the default tag pattern so the mock has a real pattern and version
    for use in output assertions.
    """
    real = Tagger.from_version_string(version_string)
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
    with patch("tag_sync.cli.main.resolve_packager", return_value=packager):
        yield


@contextmanager
def patch_tagger(tagger: MagicMock):
    """Patch all Tagger factory methods to return the given mock."""
    with patch("tag_sync.cli.main.Tagger") as mock_cls:
        mock_cls.from_tag_pattern.return_value = tagger
        mock_cls.from_version_string.return_value = tagger
        mock_cls.from_tag_string.return_value = tagger
        yield mock_cls


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


class TestVerify:
    def test_published(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.is_published.return_value = True

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["verify"])

        assert result.exit_code == 0
        assert "already published" in result.output

    def test_not_published(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.is_published.return_value = False

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["verify"])

        assert result.exit_code == 0
        assert "not been published" in result.output

    def test_version_string_appears_in_output(self) -> None:
        packager = mock_packager(SemVer(2, 3, 4))
        tagger = mock_tagger("2.3.4")
        tagger.is_published.return_value = True

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["verify"])

        assert "v2.3.4" in result.output

    def test_default_tag_pattern_used_when_omitted(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.is_published.return_value = False

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls:
            runner.invoke(cli, ["verify"])

        mock_cls.from_tag_pattern.assert_called_once_with(SemVer(1, 0, 0), DEFAULT_TAG_PATTERN)

    def test_custom_tag_pattern_forwarded(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.is_published.return_value = False

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls:
            runner.invoke(cli, ["verify", "--tag-pattern", "release/qastg/{version}"])

        mock_cls.from_tag_pattern.assert_called_once_with(SemVer(1, 0, 0), "release/qastg/{version}")

    def test_explicit_packager_option(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.is_published.return_value = True

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["verify", "--packager", "uv"])

        assert result.exit_code == 0

    def test_directory_option_passed_to_resolve_packager(self, tmp_path: Path) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.is_published.return_value = True

        with patch_packagers(packager), patch_tagger(tagger):
            with patch("tag_sync.cli.main.resolve_packager", return_value=packager) as mock_resolve:
                result = runner.invoke(cli, ["verify", "--directory", str(tmp_path)])

        assert result.exit_code == 0
        mock_resolve.assert_called_once_with(None, tmp_path)

    def test_detect_error_propagates(self) -> None:
        with patch("tag_sync.cli.main.resolve_packager", side_effect=TagSyncError("no manifest")):
            result = runner.invoke(cli, ["verify"])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


class TestCheck:
    def test_matching_version_succeeds(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.check.return_value = None

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["check", "1.0.0"])

        assert result.exit_code == 0
        assert "matches the package version" in result.output
        tagger.check.assert_called_once_with(packager)

    def test_mismatched_version_fails(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("2.0.0")
        tagger.check.side_effect = VersionMismatchError("version mismatch")

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["check", "2.0.0"])

        assert result.exit_code != 0

    def test_tag_appears_in_output(self) -> None:
        packager = mock_packager(SemVer(3, 1, 4))
        tagger = mock_tagger("3.1.4")
        tagger.check.return_value = None

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["check", "3.1.4"])

        assert "v3.1.4" in result.output

    def test_default_tag_pattern_used(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.check.return_value = None

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls:
            runner.invoke(cli, ["check", "1.0.0"])

        mock_cls.from_version_string.assert_called_once_with("1.0.0", DEFAULT_TAG_PATTERN)

    def test_custom_tag_pattern_forwarded(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.check.return_value = None

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls:
            runner.invoke(cli, ["check", "1.0.0", "--tag-pattern", "release/qastg/{version}"])

        mock_cls.from_version_string.assert_called_once_with("1.0.0", "release/qastg/{version}")

    def test_directory_option_passed_to_resolve_packager(self, tmp_path: Path) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.check.return_value = None

        with patch_packagers(packager), patch_tagger(tagger):
            with patch("tag_sync.cli.main.resolve_packager", return_value=packager) as mock_resolve:
                result = runner.invoke(cli, ["check", "--directory", str(tmp_path), "1.0.0"])

        assert result.exit_code == 0
        mock_resolve.assert_called_once_with(None, tmp_path)


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------


class TestPublish:
    def test_success_explicit_version(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["publish", "1.0.0"])

        assert result.exit_code == 0
        assert "published successfully" in result.output
        tagger.check.assert_called_once_with(packager)
        tagger.make_tag.assert_called_once_with(dry_run=False)
        tagger.push_tag.assert_called_once_with(dry_run=False)

    def test_explicit_version_uses_from_version_string(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls:
            runner.invoke(cli, ["publish", "1.0.0"])

        mock_cls.from_version_string.assert_called_once_with("1.0.0", DEFAULT_TAG_PATTERN)

    def test_explicit_version_custom_tag_pattern(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls:
            runner.invoke(cli, ["publish", "1.0.0", "--tag-pattern", "release/qastg/{version}"])

        mock_cls.from_version_string.assert_called_once_with("1.0.0", "release/qastg/{version}")

    def test_omitted_version_skips_check(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["publish"])

        assert result.exit_code == 0
        tagger.check.assert_not_called()

    def test_omitted_version_uses_from_tag_pattern(self) -> None:
        packager = mock_packager(SemVer(2, 3, 4))
        tagger = mock_tagger("2.3.4")

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls:
            runner.invoke(cli, ["publish"])

        mock_cls.from_tag_pattern.assert_called_once_with(SemVer(2, 3, 4), DEFAULT_TAG_PATTERN)

    def test_omitted_version_custom_tag_pattern(self) -> None:
        packager = mock_packager(SemVer(3, 2, 1))
        tagger = mock_tagger("3.2.1")

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls:
            runner.invoke(cli, ["publish", "--tag-pattern", "release/qastg/{version}"])

        mock_cls.from_tag_pattern.assert_called_once_with(SemVer(3, 2, 1), "release/qastg/{version}")

    def test_dry_run(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["publish", "--dry-run", "1.0.0"])

        assert result.exit_code == 0
        tagger.make_tag.assert_called_once_with(dry_run=True)
        tagger.push_tag.assert_called_once_with(dry_run=True)

    def test_replace_confirmed_deletes_then_publishes(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.require_unpublished.side_effect = TagAlreadyPublishedError("already published")

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["publish", "--replace", "1.0.0"], input="y\n")

        assert result.exit_code == 0
        tagger.delete_local_tag.assert_called_once_with(dry_run=False)
        tagger.delete_remote_tag.assert_called_once_with(dry_run=False)
        tagger.make_tag.assert_called_once()
        tagger.push_tag.assert_called_once()

    def test_replace_declined_skips_delete(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.require_unpublished.side_effect = TagAlreadyPublishedError("already published")

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["publish", "--replace", "1.0.0"], input="n\n")

        assert result.exit_code != 0
        tagger.delete_local_tag.assert_not_called()
        tagger.delete_remote_tag.assert_not_called()
        tagger.make_tag.assert_not_called()

    def test_already_published_fails(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.require_unpublished.side_effect = TagAlreadyPublishedError("already published")

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["publish", "1.0.0"])

        assert result.exit_code != 0
        tagger.make_tag.assert_not_called()
        tagger.push_tag.assert_not_called()

    def test_check_failure_aborts_before_tag(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.check.side_effect = VersionMismatchError("mismatch")

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["publish", "1.0.0"])

        assert result.exit_code != 0
        tagger.make_tag.assert_not_called()
        tagger.push_tag.assert_not_called()

    def test_git_error_on_make_tag_fails(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.make_tag.side_effect = GitError("tag already exists")

        with patch_packagers(packager), patch_tagger(tagger):
            result = runner.invoke(cli, ["publish", "1.0.0"])

        assert result.exit_code != 0
        tagger.push_tag.assert_not_called()

    def test_directory_option_passed_to_resolve_packager(self, tmp_path: Path) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")

        with patch_packagers(packager), patch_tagger(tagger):
            with patch("tag_sync.cli.main.resolve_packager", return_value=packager) as mock_resolve:
                result = runner.invoke(cli, ["publish", "--directory", str(tmp_path), "1.0.0"])

        assert result.exit_code == 0
        mock_resolve.assert_called_once_with(None, tmp_path)


# ---------------------------------------------------------------------------
# nuke
# ---------------------------------------------------------------------------


class TestNuke:
    def test_confirmed_via_prompt(self) -> None:
        tagger = mock_tagger("1.0.0")

        with patch_tagger(tagger):
            result = runner.invoke(cli, ["nuke", "1.0.0"], input="y\n")

        assert result.exit_code == 0
        assert "removed locally" in result.output
        tagger.delete_local_tag.assert_called_once_with(dry_run=False)
        tagger.delete_remote_tag.assert_called_once_with(dry_run=False)

    def test_declined_via_prompt_aborts(self) -> None:
        tagger = mock_tagger("1.0.0")

        with patch_tagger(tagger):
            result = runner.invoke(cli, ["nuke", "1.0.0"], input="n\n")

        assert result.exit_code != 0
        tagger.delete_local_tag.assert_not_called()
        tagger.delete_remote_tag.assert_not_called()

    def test_force_skips_prompt(self) -> None:
        tagger = mock_tagger("1.0.0")

        with patch_tagger(tagger):
            result = runner.invoke(cli, ["nuke", "--force", "1.0.0"])

        assert result.exit_code == 0
        tagger.delete_local_tag.assert_called_once_with(dry_run=False)
        tagger.delete_remote_tag.assert_called_once_with(dry_run=False)

    def test_dry_run(self) -> None:
        tagger = mock_tagger("1.0.0")

        with patch_tagger(tagger):
            result = runner.invoke(cli, ["nuke", "--force", "--dry-run", "1.0.0"])

        assert result.exit_code == 0
        tagger.delete_local_tag.assert_called_once_with(dry_run=True)
        tagger.delete_remote_tag.assert_called_once_with(dry_run=True)

    def test_tag_appears_in_output(self) -> None:
        tagger = mock_tagger("2.0.0")

        with patch_tagger(tagger):
            result = runner.invoke(cli, ["nuke", "--force", "2.0.0"])

        assert "v2.0.0" in result.output

    def test_custom_tag_pattern_forwarded(self) -> None:
        tagger = mock_tagger("1.0.0")

        with patch_tagger(tagger) as mock_cls:
            runner.invoke(cli, ["nuke", "--force", "--tag-pattern", "release/qastg/{version}", "1.0.0"])

        mock_cls.from_version_string.assert_called_once_with("1.0.0", "release/qastg/{version}")

    def test_git_error_on_delete_local_fails(self) -> None:
        tagger = mock_tagger("1.0.0")
        tagger.delete_local_tag.side_effect = GitError("tag not found")

        with patch_tagger(tagger):
            result = runner.invoke(cli, ["nuke", "--force", "1.0.0"])

        assert result.exit_code != 0
        tagger.delete_remote_tag.assert_not_called()


# ---------------------------------------------------------------------------
# Config file integration — tag_pattern resolved from config when CLI omits it
# ---------------------------------------------------------------------------


CONFIG_PATTERN = "release/qastg/{version}"


@contextmanager
def patch_config(tag_pattern: str | None):
    """Patch load_config to return a TagSyncConfig with the given tag_pattern."""
    config = TagSyncConfig(tag_pattern=tag_pattern)
    with patch("tag_sync.cli.main.load_config", return_value=config):
        yield


class TestConfigIntegration:
    def test_verify_uses_config_pattern_when_no_cli_flag(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.is_published.return_value = False

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls, patch_config(CONFIG_PATTERN):
            runner.invoke(cli, ["verify"])

        mock_cls.from_tag_pattern.assert_called_once_with(SemVer(1, 0, 0), CONFIG_PATTERN)

    def test_verify_cli_flag_overrides_config(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.is_published.return_value = False

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls, patch_config(CONFIG_PATTERN):
            runner.invoke(cli, ["verify", "--tag-pattern", "other/{version}"])

        mock_cls.from_tag_pattern.assert_called_once_with(SemVer(1, 0, 0), "other/{version}")

    def test_check_uses_config_pattern_when_no_cli_flag(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.check.return_value = None

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls, patch_config(CONFIG_PATTERN):
            runner.invoke(cli, ["check", "1.0.0"])

        mock_cls.from_version_string.assert_called_once_with("1.0.0", CONFIG_PATTERN)

    def test_publish_uses_config_pattern_when_no_cli_flag(self) -> None:
        packager = mock_packager(SemVer(2, 3, 4))
        tagger = mock_tagger("2.3.4")

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls, patch_config(CONFIG_PATTERN):
            runner.invoke(cli, ["publish"])

        mock_cls.from_tag_pattern.assert_called_once_with(SemVer(2, 3, 4), CONFIG_PATTERN)

    def test_publish_cli_flag_overrides_config(self) -> None:
        packager = mock_packager(SemVer(2, 3, 4))
        tagger = mock_tagger("2.3.4")

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls, patch_config(CONFIG_PATTERN):
            runner.invoke(cli, ["publish", "--tag-pattern", "other/{version}"])

        mock_cls.from_tag_pattern.assert_called_once_with(SemVer(2, 3, 4), "other/{version}")

    def test_nuke_uses_config_pattern_when_no_cli_flag(self) -> None:
        tagger = mock_tagger("1.0.0")

        with patch_tagger(tagger) as mock_cls, patch_config(CONFIG_PATTERN):
            runner.invoke(cli, ["nuke", "--force", "1.0.0"])

        mock_cls.from_version_string.assert_called_once_with("1.0.0", CONFIG_PATTERN)

    def test_falls_back_to_default_when_no_config_and_no_flag(self) -> None:
        packager = mock_packager(SemVer(1, 0, 0))
        tagger = mock_tagger("1.0.0")
        tagger.is_published.return_value = False

        with patch_packagers(packager), patch_tagger(tagger) as mock_cls:
            with patch("tag_sync.cli.main.load_config", return_value=None):
                runner.invoke(cli, ["verify"])

        mock_cls.from_tag_pattern.assert_called_once_with(SemVer(1, 0, 0), DEFAULT_TAG_PATTERN)
