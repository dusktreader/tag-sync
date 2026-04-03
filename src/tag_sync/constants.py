from typing import Literal

from bidict import bidict


PRETYPE_CANONICAL = Literal["alpha", "beta", "rc", "dev"]
type PretypeMap = bidict[str, PRETYPE_CANONICAL]
