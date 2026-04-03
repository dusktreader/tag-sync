Feature: verify command

  Background:
    Given a git repository with version "1.2.3" in pyproject.toml

  Scenario: version is already published
    Given the tag "v1.2.3" exists on the upstream
    When I run "verify"
    Then the command succeeds
    And the output contains "already published"
    And the output contains "v1.2.3"

  Scenario: version has not been published yet
    Given no tags exist on the upstream
    When I run "verify"
    Then the command succeeds
    And the output contains "not been published"
    And the output contains "v1.2.3"
