from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from typerdrive import add_logs_subcommand, handle_errors, terminal_message

from tag_sync.exceptions import TagAlreadyPublishedError
from tag_sync.packager import PACKAGERS, resolve_packager
from tag_sync.pattern import Pattern
from tag_sync.tagger import Tagger

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


@cli.command()
@handle_errors("verify failed")
def verify(
    packager_name: PackagerOption = None,
    directory: DirectoryOption = Path("."),
) -> None:
    """
    Verify whether the current package version has a published git tag.

    Uses the tagger's default pattern to convert the package's SemVer to a
    canonical tag string, then checks whether that tag exists on origin.

    The packager is auto-detected from the project directory when --packager
    is not supplied.
    """
    packager = resolve_packager(packager_name, directory)
    package_version = packager.package_version
    default_pattern = Pattern(Tagger.DEFAULT_PATTERN_TEMPLATE)
    tagger = Tagger(default_pattern.format(package_version))
    version_string = tagger.pattern.format(tagger.version)
    if tagger.is_published():
        suffix = "is already published."
    else:
        suffix = "has not been published yet."
    terminal_message(f"Version [cyan]{version_string}[/cyan] {suffix}", subject="verify")


@cli.command()
@handle_errors("check failed")
def check(
    tag_version_string: Annotated[
        str, typer.Argument(help="Tag version string to validate against the package version")
    ],
    packager_name: PackagerOption = None,
    directory: DirectoryOption = Path("."),
) -> None:
    """
    Validate that a tag version matches the current package version.

    The packager is auto-detected from the project directory when --packager
    is not supplied.
    """
    logger.debug(f"Checking tag version: {tag_version_string}")
    packager = resolve_packager(packager_name, directory)
    tagger = Tagger(tag_version_string)
    tagger.check(packager)
    version_string = tagger.pattern.format(tagger.version)
    terminal_message(f"Version [cyan]{version_string}[/cyan] matches the package version.", subject="check")


@cli.command()
@handle_errors("publish failed")
def publish(
    tag_version_string: Annotated[
        str | None, typer.Argument(help="Tag version string to publish. Derived from the package version when omitted.")
    ] = None,
    packager_name: PackagerOption = None,
    directory: DirectoryOption = Path("."),
    replace: Annotated[bool, typer.Option(help="Replace existing tag if it exists")] = False,
    dry_run: DryRunOption = False,
) -> None:
    """
    Validate the project version, create a git tag, and push it to origin.

    When the tag version string is supplied it is validated against the current
    package version.  When omitted it is derived from the package version using
    the default tag pattern, skipping the version-match check.

    If the tag is already published on origin the command fails unless
    --replace is given, in which case the existing tag is deleted locally and
    on origin before the new one is created.

    The packager is auto-detected from the project directory when --packager
    is not supplied.
    """
    packager = resolve_packager(packager_name, directory)
    explicit = tag_version_string is not None
    if tag_version_string is None:
        default_pattern = Pattern(Tagger.DEFAULT_PATTERN_TEMPLATE)
        tag_version_string = default_pattern.format(packager.package_version)
    tag: str = tag_version_string
    tagger = Tagger(tag)
    if explicit:
        tagger.check(packager)
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
    version_string = tagger.pattern.format(tagger.version)
    terminal_message(
        f"Tag [cyan]{version_string}[/cyan] published successfully.",
        subject="publish",
    )


@cli.command()
@handle_errors("nuke failed")
def nuke(
    tag_version_string: Annotated[str, typer.Argument(help="Tag version string to remove locally and on origin")],
    force: Annotated[bool | None, typer.Option(help="Don't prompt to confirm deletion")] = None,
    dry_run: DryRunOption = False,
) -> None:
    """
    Remove a tag from both the local git repository and origin.
    """
    if force is None:
        force = typer.confirm(
            f"Are you sure you want to nuke tag {tag_version_string}? This will delete it locally and on origin."
        )
    if not force:
        raise typer.Abort()
    tagger = Tagger(tag_version_string)
    logger.debug(f"Nuking tag: {tag_version_string}")
    tagger.delete_local_tag(dry_run=dry_run)
    tagger.delete_remote_tag(dry_run=dry_run)
    version_string = tagger.pattern.format(tagger.version)
    terminal_message(
        f"Tag [cyan]{version_string}[/cyan] removed locally and from origin.",
        subject="nuke",
    )
