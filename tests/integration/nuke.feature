Feature: nuke command

  Background:
    Given a git repository with version "1.2.3" in pyproject.toml

  Scenario: nuke a tag with --force
    Given the tag "v1.2.3" exists locally and on the upstream
    When I run "nuke" with argument "v1.2.3" and flag "--force"
    Then the command succeeds
    And the output contains "removed locally"
    And the tag "v1.2.3" does not exist locally
    And the tag "v1.2.3" does not exist on the upstream

  Scenario: nuke confirmed via prompt
    Given the tag "v1.2.3" exists locally and on the upstream
    When I run "nuke" with argument "v1.2.3" confirmed via prompt
    Then the command succeeds
    And the tag "v1.2.3" does not exist locally
    And the tag "v1.2.3" does not exist on the upstream

  Scenario: nuke declined via prompt leaves tags intact
    Given the tag "v1.2.3" exists locally and on the upstream
    When I run "nuke" with argument "v1.2.3" declined via prompt
    Then the command fails
    And the tag "v1.2.3" exists locally
    And the tag "v1.2.3" exists on the upstream

  Scenario: dry run does not delete tags
    Given the tag "v1.2.3" exists locally and on the upstream
    When I run "nuke" with argument "v1.2.3" and flags "--force" "--dry-run"
    Then the command succeeds
    And the tag "v1.2.3" exists locally
    And the tag "v1.2.3" exists on the upstream
