"""Step definitions for nuke.feature."""

import pytest
from pytest_bdd import scenarios, when

scenarios("../nuke.feature")

pytestmark = pytest.mark.integration


@when('I run "nuke" with argument "1.2.3" and flag "--force"')
def run_nuke_force(bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("nuke", "--force", "1.2.3")


@when('I run "nuke" with argument "1.2.3" confirmed via prompt')
def run_nuke_confirmed(bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("nuke", "1.2.3", input="y\n")


@when('I run "nuke" with argument "1.2.3" declined via prompt')
def run_nuke_declined(bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("nuke", "1.2.3", input="n\n")


@when('I run "nuke" with argument "1.2.3" and flags "--force" "--dry-run"')
def run_nuke_force_dry_run(bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("nuke", "--force", "--dry-run", "1.2.3")
