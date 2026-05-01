"""Step definitions for publish.feature."""

import pytest
from pytest_bdd import scenarios, when

scenarios("../publish.feature")

pytestmark = pytest.mark.integration


@when('I run "publish" with argument "1.2.3"')
def run_publish(bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("publish", "1.2.3")


@when('I run "publish" with argument "2.0.0"')
def run_publish_mismatch(bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("publish", "2.0.0")


@when('I run "publish" with argument "1.2.3" and flag "--dry-run"')
def run_publish_dry_run(bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("publish", "--dry-run", "1.2.3")


@when('I run "publish" with argument "1.2.3" and flag "--replace" confirmed')
def run_publish_replace_confirmed(bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("publish", "--replace", "1.2.3", input="y\n")


@when('I run "publish" with argument "1.2.3" and flag "--replace" declined')
def run_publish_replace_declined(bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("publish", "--replace", "1.2.3", input="n\n")


@when('I run "publish" without a tag argument')
def run_publish_no_arg(bdd_context: dict, run_tag_sync) -> None:
    bdd_context["result"] = run_tag_sync("publish")
