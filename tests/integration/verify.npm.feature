Feature: verify command (npm)

  Background:
    Given a git repository with version "1.2.3-alpha.1" in package.json

  Scenario: version is already published
    Given the tag "v1.2.3-alpha.1" exists on the upstream
    When I run "verify" with packager "npm"
    Then the command succeeds
    And the output contains "already published"
    And the output contains "v1.2.3-alpha.1"

  Scenario: version has not been published yet
    Given no tags exist on the upstream
    When I run "verify" with packager "npm"
    Then the command succeeds
    And the output contains "not been published"
    And the output contains "v1.2.3-alpha.1"
