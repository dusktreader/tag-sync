from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from typerdrive import add_logs_subcommand, handle_errors, terminal_message

from tag_sync.config import load_config
from tag_sync.exceptions import TagAlreadyPublishedError
from tag_sync.packager import PACKAGERS, resolve_packager
from tag_sync.tagger import DEFAULT_TAG_PATTERN, TAG_NAME_VERSION_PLACEHOLDER, Tagger

cli = typer.Typer(
    name="tag-sync",
    help="Sync git tags with project versions.",
    no_args_is_help=True,
)

add_logs_subcommand(cli)

DryRunOption = Annotated[bool, typer.Option("--dry-run", help="Show what would happen without making any changes")]
PackagerOption = Annotated[
    str | None,
    typer.Option(
        "--packager",
        help=f"Packager to use for reading the project version. One of: {', '.join(PACKAGERS)}. Auto-detected when omitted.",
    ),
]
DirectoryOption = Annotated[
    Path,
    typer.Option(
        "--directory",
        "-d",
        help="Directory containing the project. Defaults to the current working directory.",
    ),
]
TagPatternOption = Annotated[
    str | None,
    typer.Option(
        "--tag-pattern",
        help=(
            f"Template for the git tag name. Must contain {TAG_NAME_VERSION_PLACEHOLDER!r} as the placeholder for "
            f"the bare semver (e.g. '1.2.3'). Defaults to {DEFAULT_TAG_PATTERN!r}, which produces tags like 'v1.2.3'. "
            f"Example: 'release/qastg/{{version}}' produces 'release/qastg/1.2.3'. "
            f"Can also be set via a project config file (.tag-sync.toml, .tag-sync.json, etc.)."
        ),
    ),
]


def _effective_tag_pattern(cli_value: str | None, directory: Path) -> str:
    """
    Resolve the effective tag pattern, with CLI taking precedence over config.

    Priority order:
    1. Explicit `--tag-pattern` on the command line.
    2. `tag_pattern` from the project config file (if present).
    3. `DEFAULT_TAG_PATTERN` (`v{version}`).
    """
    if cli_value is not None:
        return cli_value
    config = load_config(directory)
    if config is not None and config.tag_pattern is not None:
        return config.tag_pattern
    return DEFAULT_TAG_PATTERN


@cli.command()
@handle_errors("verify failed")
def verify(
    packager_name: PackagerOption = None,
    directory: DirectoryOption = Path("."),
    tag_pattern: TagPatternOption = None,
) -> None:
    """
    Verify whether the current package version has a published git tag.

    Derives the tag name from the package version using `--tag-pattern`
    (default: `v{version}`), then checks whether that tag exists on origin.

    The packager is auto-detected from the project directory when `--packager`
    is not supplied.
    """
    packager = resolve_packager(packager_name, directory)
    effective_pattern = _effective_tag_pattern(tag_pattern, directory)
    tagger = Tagger.from_tag_pattern(packager.package_version, effective_pattern)
    version_string = tagger.pattern.format(tagger.version)
    if tagger.is_published():
        suffix = "is already published."
    else:
        suffix = "has not been published yet."
    terminal_message(f"Version [cyan]{version_string}[/cyan] {suffix}", subject="verify")


@cli.command()
@handle_errors("check failed")
def check(
    version_string: Annotated[
        str, typer.Argument(help="Bare semver or tag name to validate against the package version (e.g. 1.2.3 or v1.2.3)")
    ],
    packager_name: PackagerOption = None,
    directory: DirectoryOption = Path("."),
    tag_pattern: TagPatternOption = None,
) -> None:
    """
    Validate that a version matches the current package version.

    The `--tag-pattern` (or project config) controls the full tag name that
    would be created for this version.  Defaults to `v{version}`.

    The packager is auto-detected from the project directory when `--packager`
    is not supplied.
    """
    logger.debug(f"Checking version: {version_string}")
    packager = resolve_packager(packager_name, directory)
    effective_pattern = _effective_tag_pattern(tag_pattern, directory)
    tagger = Tagger.from_version_or_tag_string(version_string, effective_pattern)
    tagger.check(packager)
    tag = tagger.pattern.format(tagger.version)
    terminal_message(f"Tag [cyan]{tag}[/cyan] matches the package version.", subject="check")


@cli.command()
@handle_errors("publish failed")
def publish(
    version_string: Annotated[
        str | None,
        typer.Argument(help="Bare semver or tag name to publish (e.g. 1.2.3 or v1.2.3). Derived from the package version when omitted."),
    ] = None,
    packager_name: PackagerOption = None,
    directory: DirectoryOption = Path("."),
    replace: Annotated[bool, typer.Option(help="Replace existing tag if it exists")] = False,
    dry_run: DryRunOption = False,
    tag_pattern: TagPatternOption = None,
) -> None:
    """
    Validate the project version, create a git tag, and push it to origin.

    The `--tag-pattern` controls the full tag name (default: `v{version}`).

    When a version is supplied it is validated against the current package
    version.  When omitted the package version is used directly, skipping the
    version-match check.

    If the tag is already published on origin the command fails unless
    `--replace` is given, in which case the existing tag is deleted locally
    and on origin before the new one is created.

    The packager is auto-detected from the project directory when `--packager`
    is not supplied.
    """
    packager = resolve_packager(packager_name, directory)
    effective_pattern = _effective_tag_pattern(tag_pattern, directory)

    if version_string is not None:
        tagger = Tagger.from_version_or_tag_string(version_string, effective_pattern)
        tagger.check(packager)
    else:
        tagger = Tagger.from_tag_pattern(packager.package_version, effective_pattern)

    tag = tagger.pattern.format(tagger.version)
    try:
        tagger.require_unpublished()
    except TagAlreadyPublishedError:
        if not replace:
            raise
        if not typer.confirm(f"Tag {tag} is already on origin. Replace it?"):
            raise typer.Abort()
        logger.debug(f"Replacing tag: {tag}")
        tagger.delete_local_tag(dry_run=dry_run)
        tagger.delete_remote_tag(dry_run=dry_run)
    logger.debug(f"Publishing tag: {tag}")
    tagger.make_tag(dry_run=dry_run)
    tagger.push_tag(dry_run=dry_run)
    terminal_message(f"Tag [cyan]{tag}[/cyan] published successfully.", subject="publish")


@cli.command()
@handle_errors("nuke failed")
def nuke(
    version_string: Annotated[
        str, typer.Argument(help="Bare semver or tag name of the tag to remove locally and on origin (e.g. 1.2.3 or v1.2.3)")
    ],
    force: Annotated[bool | None, typer.Option(help="Don't prompt to confirm deletion")] = None,
    dry_run: DryRunOption = False,
    tag_pattern: TagPatternOption = None,
    directory: DirectoryOption = Path("."),
) -> None:
    """
    Remove a tag from both the local git repository and origin.

    The `--tag-pattern` (or project config) controls the full tag name
    (default: `v{version}`).
    """
    effective_pattern = _effective_tag_pattern(tag_pattern, directory)
    tagger = Tagger.from_version_or_tag_string(version_string, effective_pattern)
    tag = tagger.pattern.format(tagger.version)
    if force is None:
        force = typer.confirm(
            f"Are you sure you want to nuke tag {tag}? This will delete it locally and on origin."
        )
    if not force:
        raise typer.Abort()
    logger.debug(f"Nuking tag: {tag}")
    tagger.delete_local_tag(dry_run=dry_run)
    tagger.delete_remote_tag(dry_run=dry_run)
    terminal_message(f"Tag [cyan]{tag}[/cyan] removed locally and from origin.", subject="nuke")
