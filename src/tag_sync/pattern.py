import re
from typing import cast

from bidict import bidict
import snick

from tag_sync.constants import PRETYPE_CANONICAL, PretypeMap
from tag_sync.exceptions import InvalidPatternError, VersionParseError
from tag_sync.semver import SemVer


# Parses: [prefix]<major>.<minor>.<patch>[<pre_leader>]<pre_type:t1|t2|...>[<pre_sep>]<pre_id>
# Examples:
#   v<major>.<minor>.<patch>-<pre_type:alpha|beta|rc|dev>.<pre_id> -> v1.2.3, v1.2.3-alpha.1, etc
#   <major>.<minor>.<patch><pre_type:a|b|rc|dev><pre_id>           -> 1.2.3, 1.2.3a1, etc
PATTERN_TEMPLATE = re.compile(
    r"^(?P<prefix>.*?)"
    r"<major>\.<minor>\.<patch>"
    r"(?P<pre_leader>.*?)<pre_type:(?P<pre_types>[^>]+)>(?P<pre_sep>.*?)<pre_id>"
    r"$"
)


class Pattern:
    template: str

    def __init__(self, template: str, pretype_map: "dict[str, PRETYPE_CANONICAL] | None" = None) -> None:
        match = InvalidPatternError.enforce_defined(
            PATTERN_TEMPLATE.match(template),
            snick.dedent(
                f"""
                 Pattern template is not valid: {template!r}
                 Expected format: [prefix]<major>.<minor>.<patch>[<pre_leader>]<pre_type:t1|t2|...>[<pre_sep>]<pre_id>
                """
            ),
        )
        self.template = template
        base: PretypeMap = bidict(pretype_map) if pretype_map is not None else bidict()
        # Ensure every canonical pre-type that isn't already a value in the
        # supplied map gets an identity entry (raw == canonical).
        canonical_types: tuple[PRETYPE_CANONICAL, ...] = ("alpha", "beta", "rc", "dev")
        supplemental = {c: c for c in canonical_types if c not in base.inverse}
        self.pretype_map: PretypeMap = bidict({**base, **supplemental})

        prefix = match.group("prefix") or ""
        pre_leader = match.group("pre_leader") or ""
        pre_sep = match.group("pre_sep") or ""
        self._pre_types = match.group("pre_types").split("|")

        self.core_format_string = f"{prefix}{{major}}.{{minor}}.{{patch}}"
        self.pre_format_string = f"{pre_leader}{{pre_type}}{pre_sep}{{pre_id}}"

        pre_type_alt = "|".join(self._pre_types)
        core = rf"^{prefix}(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
        pre = rf"(?:{re.escape(pre_leader)}(?P<pre_type>{pre_type_alt}){re.escape(pre_sep)}(?P<pre_id>\d+))?"
        self.regex = core + pre + r"$"

    def parse(self, version_string: str) -> SemVer:
        """
        Parse a version string against this pattern and return a SemVer.

        Raises:
            VersionParseError: If the string does not match the pattern.
        """
        message: str = snick.dedent(
            f"""
            Invalid version string: {version_string}

            Please use format {self.template}.

            Examples:
            """
        )
        message += "\n".join(f"- {ex}" for ex in self.examples)
        match = VersionParseError.enforce_defined(
            re.match(self.regex, version_string),
            message,
        )
        with VersionParseError.handle_errors(f"Couldn't parse version from {version_string}"):
            version = SemVer(
                major=int(match.group("major")),
                minor=int(match.group("minor")),
                patch=int(match.group("patch")),
            )
            if match.group("pre_type"):
                raw = match.group("pre_type")
                version.pre_type = cast(PRETYPE_CANONICAL, self.pretype_map.get(raw, raw))
                version.pre_id = int(match.group("pre_id"))
            return version

    def format(self, version: SemVer) -> str:
        """
        Produce a version string from the given SemVer using this Pattern.

        Canonical pre_type values (e.g. 'alpha') are mapped back to their
        pattern-native form (e.g. 'a') via the inverse of pretype_map before
        substitution.
        """
        result = self.core_format_string.format(major=version.major, minor=version.minor, patch=version.patch)
        if version.pre_type is not None and version.pre_id is not None:
            raw_pre_type = self.pretype_map.inverse.get(version.pre_type, version.pre_type)
            result += self.pre_format_string.format(pre_type=raw_pre_type, pre_id=version.pre_id)
        return result

    @property
    def examples(self) -> list[str]:
        """
        Return four representative example version strings: two release
        versions and two pre-release versions with fixed values.
        """
        pt0 = self._pre_types[0]
        pt1 = self._pre_types[min(1, len(self._pre_types) - 1)]
        return [
            self.format(SemVer(major=1, minor=0, patch=0)),
            self.format(SemVer(major=1, minor=2, patch=3)),
            self.format(SemVer(major=2, minor=0, patch=0, pre_type=self.pretype_map[pt0], pre_id=1)),
            self.format(SemVer(major=1, minor=2, patch=3, pre_type=self.pretype_map[pt1], pre_id=2)),
        ]
