from typerdrive import TyperdriveError


class TagSyncError(TyperdriveError):
    """Base exception for all tag-sync errors."""


class InvalidPatternError(TagSyncError):
    """Raised when a Pattern regex is missing required named groups."""


class VersionParseError(TagSyncError):
    """Raised when a version string cannot be parsed."""


class VersionMismatchError(TagSyncError):
    """Raised when a tag version does not match the package version."""


class GitError(TagSyncError):
    """Raised when a git operation fails."""


class TagAlreadyPublishedError(TagSyncError):
    """Raised when a tag is already published on origin and replacement was not requested."""
