import snick
from git import Repo

from tag_sync.constants import PRETYPE_CANONICAL
from tag_sync.exceptions import GitError, TagAlreadyPublishedError, VersionMismatchError
from tag_sync.packager import Packager
from tag_sync.pattern import Pattern
from tag_sync.semver import SemVer


class Tagger:
    pattern: Pattern
    version: SemVer

    DEFAULT_PATTERN_TEMPLATE = "v<major>.<minor>.<patch>-<pre_type:alpha|beta|rc|dev>.<pre_id>"

    def __init__(
        self,
        version_string: str,
        pattern_template: str | None = None,
        pretype_map: "dict[str, PRETYPE_CANONICAL] | None" = None,
    ):
        self.pattern = Pattern(
            pattern_template if pattern_template is not None else self.DEFAULT_PATTERN_TEMPLATE,
            pretype_map=pretype_map,
        )
        self.version = self.parse(version_string)

    def parse(self, version_string: str) -> SemVer:
        return self.pattern.parse(version_string)

    def check(self, packager: Packager) -> None:
        """
        Verify that the version from the packager matches this tag version.

        Raises:
            VersionMismatchError: If the versions do not match.
        """
        package_version = packager.package_version
        VersionMismatchError.require_condition(
            self.version == package_version,
            snick.dedent(
                f"""
                Package version doesn't match tag version.

                Tag version:     {self.pattern.format(self.version)}
                Package version: {packager.pattern.format(package_version)}

                Please update the package version.
                """
            ),
        )

    def is_published(self) -> bool:
        """Check whether this tag exists on the remote."""
        tag = self.pattern.format(self.version)
        repo = Repo(search_parent_directories=True)
        refs = repo.git.ls_remote("--tags", "origin", tag)
        return bool(refs.strip())

    def require_unpublished(self) -> None:
        """
        Raise `TagAlreadyPublishedError` if this tag is already on origin.

        Raises:
            TagAlreadyPublishedError: If the tag is already published.
        """
        tag = self.pattern.format(self.version)
        TagAlreadyPublishedError.require_condition(
            not self.is_published(),
            f"Tag {tag} is already published on origin. Use --replace to overwrite it.",
        )

    def make_tag(self, dry_run: bool = False) -> None:
        """Create this tag in the local git repository."""
        tag = self.pattern.format(self.version)
        if dry_run:
            print(f"[dry-run] Would create tag: {tag}")
            return
        repo = Repo(search_parent_directories=True)
        with GitError.handle_errors(f"Failed to create tag {tag}"):
            repo.create_tag(tag)

    def push_tag(self, dry_run: bool = False) -> None:
        """Push this tag to the remote."""
        tag = self.pattern.format(self.version)
        if dry_run:
            print(f"[dry-run] Would push tag: {tag}")
            return
        repo = Repo(search_parent_directories=True)
        with GitError.handle_errors(f"Failed to push tag {tag}"):
            repo.remotes["origin"].push(tag)

    def delete_local_tag(self, dry_run: bool = False) -> None:
        """Delete this tag from the local git repository."""
        tag = self.pattern.format(self.version)
        if dry_run:
            print(f"[dry-run] Would delete local tag: {tag}")
            return
        repo = Repo(search_parent_directories=True)
        with GitError.handle_errors(f"Failed to delete local tag {tag}"):
            repo.delete_tag(repo.tag(f"refs/tags/{tag}"))

    def delete_remote_tag(self, dry_run: bool = False) -> None:
        """Delete this tag from the remote."""
        tag = self.pattern.format(self.version)
        if dry_run:
            print(f"[dry-run] Would delete remote tag: {tag}")
            return
        repo = Repo(search_parent_directories=True)
        with GitError.handle_errors(f"Failed to delete remote tag {tag}"):
            repo.remotes["origin"].push(refspec=f":refs/tags/{tag}")
