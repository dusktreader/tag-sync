"""Step definitions for verify.autodetect.feature and check.autodetect.feature."""

import pytest
from pytest_bdd import parsers, scenarios, when

scenarios("../verify.autodetect.feature")
scenarios("../check.autodetect.feature")

pytestmark = pytest.mark.integration


@when('I run "verify" without specifying a packager')
def run_verify_autodetect(bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("verify")


@when(parsers.parse('I run "check" with argument "{arg}" without specifying a packager'))
def run_check_with_arg_autodetect(arg: str, bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("check", arg)
