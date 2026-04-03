"""Step definitions for verify.npm.feature and check.npm.feature."""

import pytest
from pytest_bdd import parsers, scenarios, when

scenarios("../verify.npm.feature")
scenarios("../check.npm.feature")

pytestmark = pytest.mark.integration


@when('I run "verify" with packager "npm"')
def run_verify_npm(bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("verify", "--packager", "npm")


@when(parsers.parse('I run "check" with argument "{arg}" with packager "npm"'))
def run_check_with_arg_npm(arg: str, bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("check", arg, "--packager", "npm")
