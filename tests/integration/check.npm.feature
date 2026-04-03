Feature: check command (npm)

  Background:
    Given a git repository with version "1.2.3" in package.json

  Scenario: tag version matches package version
    Given the tag "v1.2.3" exists locally
    When I run "check" with argument "v1.2.3" with packager "npm"
    Then the command succeeds
    And the output contains "matches the package version"

  Scenario: tag version does not match package version
    Given the tag "v2.0.0" exists locally
    When I run "check" with argument "v2.0.0" with packager "npm"
    Then the command fails
