"""Step definitions for check.feature."""

import pytest
from pytest_bdd import parsers, scenarios, when

scenarios("../check.feature")

pytestmark = pytest.mark.integration


@when(parsers.parse('I run "check" with argument "{arg}"'))
def run_check_with_arg(arg: str, bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("check", arg)
