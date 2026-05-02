import json
import tomllib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol, override

from packaging.version import Version

from tag_sync.exceptions import TagSyncError, VersionParseError
from tag_sync.pattern import Pattern
from tag_sync.semver import SemVer


_PRE_TYPE_MAP: dict[str, str] = {"a": "alpha", "b": "beta", "rc": "rc"}


def _packaging_version_to_semver(v: Version) -> SemVer:
    """
    Convert a `packaging.version.Version` to a `SemVer`.

    Handles two-part versions (`1.2` → patch=0), standard pre-releases
    (`a`, `b`, `rc`), and dev releases (`1.2.3.dev3`). Post-releases are
    not supported and raise `VersionParseError`.
    """
    if v.post is not None:
        raise VersionParseError(f"Post-release versions are not supported: {v}")
    pre_type = None
    pre_id = None
    if v.pre is not None:
        tag, num = v.pre
        pre_type = _PRE_TYPE_MAP.get(tag, tag)  # type: ignore[assignment]
        pre_id = num
    elif v.dev is not None:
        pre_type = "dev"
        pre_id = v.dev
    return SemVer(major=v.major, minor=v.minor, patch=v.micro, pre_type=pre_type, pre_id=pre_id)


def _semver_to_python_version_string(semver: SemVer) -> str:
    """
    Produce a canonical Python version string from a `SemVer`.

    The inverse of `_packaging_version_to_semver`: maps canonical pre-type
    names back to the single-letter PEP 440 forms used by pip/uv.
    """
    _CANONICAL_TO_PEP440: dict[str, str] = {"alpha": "a", "beta": "b", "rc": "rc", "dev": ".dev"}
    base = f"{semver.major}.{semver.minor}.{semver.patch}"
    if semver.pre_type is None:
        return base
    tag = _CANONICAL_TO_PEP440.get(semver.pre_type, semver.pre_type)
    if tag == ".dev":
        return f"{base}.dev{semver.pre_id}"
    return f"{base}{tag}{semver.pre_id}"


class Packager(ABC):
    pattern: Pattern

    def parse(self, version_string: str) -> SemVer:
        return self.pattern.parse(version_string)

    @abstractmethod
    def extract_version_string(self) -> str: ...

    def format(self, version: SemVer) -> str:
        return self.pattern.format(version)

    @property
    def package_version(self) -> SemVer:
        with VersionParseError.handle_errors(f"Couldn't extract package version using `{self.__class__.__name__}`"):
            return self.parse(self.extract_version_string())


class UvPackager(Packager):
    def __init__(self, path: Path = Path(".")):
        self.path = path
        self.pattern = Pattern(
            "<major>.<minor>.<patch><pre_type:a|b|rc|dev><pre_id>",
            pretype_map={"a": "alpha", "b": "beta"},
        )

    @override
    def parse(self, version_string: str) -> SemVer:
        with VersionParseError.handle_errors(f"Couldn't parse Python version: {version_string!r}"):
            return _packaging_version_to_semver(Version(version_string))

    @override
    def format(self, version: SemVer) -> str:
        return _semver_to_python_version_string(version)

    @override
    def extract_version_string(self) -> str:
        pyproject_path = self.path / "pyproject.toml"
        data = tomllib.loads(pyproject_path.read_text())
        return data["project"]["version"]


class NpmPackager(Packager):
    def __init__(self, path: Path = Path(".")):
        self.path = path
        self.pattern = Pattern("<major>.<minor>.<patch>-<pre_type:alpha|beta|rc|dev>.<pre_id>")

    @override
    def extract_version_string(self) -> str:
        package_json_path = self.path / "package.json"
        data = json.loads(package_json_path.read_text())
        return data["version"]


class _PackagerFactory(Protocol):
    def __call__(self, path: Path = ...) -> Packager: ...


PACKAGERS: dict[str, _PackagerFactory] = {
    "npm": NpmPackager,
    "uv": UvPackager,
}

_MANIFEST_PACKAGER: dict[str, str] = {
    "pyproject.toml": "uv",
    "package.json": "npm",
}


def resolve_packager(packager_name: str | None, path: Path = Path(".")) -> Packager:
    """
    Return an instantiated `Packager` for the given directory.

    When `packager_name` is `None` the packager is auto-detected from the
    manifest files present in `path`.  When a name is provided it is looked up
    in the `PACKAGERS` registry and instantiated with `path`.

    Args:
        packager_name: Explicit packager key (e.g. `"uv"`, `"npm"`), or `None`
            to trigger auto-detection.
        path: Project directory to pass to the packager.

    Returns:
        An instantiated `Packager`.
    """
    if packager_name is None:
        return detect_packager(path)
    return PACKAGERS[packager_name](path)


def detect_packager(path: Path = Path(".")) -> Packager:
    """
    Auto-detect the packager from manifest files in `path`.

    Looks for `pyproject.toml` (uv) and `package.json` (npm).  Raises
    `TagSyncError` when zero or more than one manifest is found — the caller
    should use `--packager` to be explicit in that case.

    Args:
        path: Directory to inspect.  Defaults to the current working directory.

    Returns:
        An instantiated `Packager` for the detected manifest.

    Raises:
        TagSyncError: When no manifest or multiple manifests are found.
    """
    found = [name for name in _MANIFEST_PACKAGER if (path / name).exists()]
    if len(found) == 0:
        raise TagSyncError(
            f"No supported manifest file found in {path}. "
            f"Expected one of: {', '.join(_MANIFEST_PACKAGER)}. "
            "Use --packager to specify the packager explicitly."
        )
    if len(found) > 1:
        raise TagSyncError(
            f"Multiple manifest files found in {path}: {', '.join(found)}. "
            "Use --packager to specify the packager explicitly."
        )
    packager_name = _MANIFEST_PACKAGER[found[0]]
    return PACKAGERS[packager_name](path)
