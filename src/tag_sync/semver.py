from dataclasses import dataclass

from tag_sync.constants import PRETYPE_CANONICAL


@dataclass
class SemVer:
    major: int
    minor: int
    patch: int
    pre_type: PRETYPE_CANONICAL | None = None
    pre_id: int | None = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (self.major, self.minor, self.patch, self.pre_type, self.pre_id) == (
            other.major,
            other.minor,
            other.patch,
            other.pre_type,
            other.pre_id,
        )

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.pre_type, self.pre_id))
