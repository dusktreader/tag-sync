"""Step definitions for verify.feature."""

import pytest
from pytest_bdd import scenarios, when

scenarios("../verify.feature")

pytestmark = pytest.mark.integration


@when('I run "verify"')
def run_verify(bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("verify")
