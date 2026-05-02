import snick
from git import Repo

from tag_sync.constants import PRETYPE_CANONICAL
from tag_sync.exceptions import GitError, TagAlreadyPublishedError, VersionMismatchError
from tag_sync.packager import Packager
from tag_sync.pattern import Pattern
from tag_sync.semver import SemVer

# Placeholder used in tag name templates to mark the version substitution site.
TAG_NAME_VERSION_PLACEHOLDER = "{version}"

# Default tag name template: prefix the bare semver with "v".
DEFAULT_TAG_PATTERN = "v{version}"

# Pattern template that produces a bare semver with no prefix (e.g. "1.2.3").
_BARE_SEMVER_PATTERN_TEMPLATE = "<major>.<minor>.<patch>-<pre_type:alpha|beta|rc|dev>.<pre_id>"


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

    @classmethod
    def _pattern_template_from_tag_pattern(cls, tag_pattern: str) -> str:
        """Derive a `Pattern`-compatible template string from a tag name template."""
        idx = tag_pattern.find(TAG_NAME_VERSION_PLACEHOLDER)
        prefix = tag_pattern[:idx]
        suffix = tag_pattern[idx + len(TAG_NAME_VERSION_PLACEHOLDER):]
        return f"{prefix}{_BARE_SEMVER_PATTERN_TEMPLATE}{suffix}"

    @classmethod
    def from_tag_pattern(cls, semver: SemVer, tag_pattern: str = DEFAULT_TAG_PATTERN) -> "Tagger":
        """
        Construct a `Tagger` from a `SemVer` and a tag name template.

        The `tag_pattern` must contain `{version}`, which is replaced with the
        bare semver string (no `v` prefix, e.g. `1.2.3` or `1.2.3-alpha.1`).
        The resulting full tag is parsed back using a pattern derived from
        `tag_pattern` so that all git operations use the correct tag name.

        Example:
            `Tagger.from_tag_pattern(SemVer(1, 2, 3), "release/qastg/{version}")`
            produces a `Tagger` whose git tag is `"release/qastg/1.2.3"`.
        """
        bare_pattern = Pattern(_BARE_SEMVER_PATTERN_TEMPLATE)
        bare_version = bare_pattern.format(semver)
        idx = tag_pattern.find(TAG_NAME_VERSION_PLACEHOLDER)
        prefix = tag_pattern[:idx]
        suffix = tag_pattern[idx + len(TAG_NAME_VERSION_PLACEHOLDER):]
        full_tag = f"{prefix}{bare_version}{suffix}"
        return cls(full_tag, pattern_template=cls._pattern_template_from_tag_pattern(tag_pattern))

    @classmethod
    def from_version_string(cls, version_string: str, tag_pattern: str = DEFAULT_TAG_PATTERN) -> "Tagger":
        """
        Construct a `Tagger` from a bare semver string and a tag name template.

        The `version_string` must be a bare semver with no prefix (e.g. `1.2.3`
        or `1.2.3-alpha.1`).  The `tag_pattern` controls the full git tag name.

        This is a convenience wrapper around `from_tag_pattern` for callers that
        have the version as a string rather than a `SemVer` object.

        Example:
            `Tagger.from_version_string("1.2.3", "release/qastg/{version}")`
            produces a `Tagger` whose git tag is `"release/qastg/1.2.3"`.
        """
        bare_pattern = Pattern(_BARE_SEMVER_PATTERN_TEMPLATE)
        semver = bare_pattern.parse(version_string)
        return cls.from_tag_pattern(semver, tag_pattern)

    @classmethod
    def from_tag_string(cls, tag_string: str, tag_pattern: str = DEFAULT_TAG_PATTERN) -> "Tagger":
        """
        Construct a `Tagger` by parsing a full tag string against a tag name template.

        The `tag_pattern` is used to derive a `Pattern` that can parse `tag_string`,
        extracting the semver from the prefix and/or suffix.  Use this when the full
        git tag name is available (e.g. from user input or `github.ref_name`) and you
        need to extract the semver and wire up git operations.

        Example:
            `Tagger.from_tag_string("release/qastg/1.2.3", "release/qastg/{version}")`
            produces a `Tagger` whose git tag is `"release/qastg/1.2.3"` and whose
            version is `SemVer(1, 2, 3)`.
        """
        return cls(tag_string, pattern_template=cls._pattern_template_from_tag_pattern(tag_pattern))

    @classmethod
    def from_version_or_tag_string(cls, string: str, tag_pattern: str = DEFAULT_TAG_PATTERN) -> "Tagger":
        """
        Construct a `Tagger` from a bare semver string or a full tag string.

        Tries to parse `string` as a bare semver first.  If that fails, parses
        it as a full tag name using `tag_pattern`.  Both paths use only the
        configured pattern — there is no cross-pattern fallback.

        This is the right constructor for user-facing inputs where either form
        is acceptable (e.g. `check` and `nuke` CLI arguments).

        Examples:
            `from_version_or_tag_string("1.2.3")` — parsed as bare semver
            `from_version_or_tag_string("v1.2.3")` — parsed as full tag name
            `from_version_or_tag_string("release/qastg/1.2.3", "release/qastg/{version}")` — full tag
        """
        try:
            return cls.from_version_string(string, tag_pattern)
        except Exception:
            return cls.from_tag_string(string, tag_pattern)

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
