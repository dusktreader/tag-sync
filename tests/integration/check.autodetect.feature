Feature: check command (auto-detect packager)

  Scenario: auto-detects uv from pyproject.toml, tag matches
    Given a git repository with version "1.2.3" in pyproject.toml
    And the tag "v1.2.3" exists locally
    When I run "check" with argument "1.2.3" without specifying a packager
    Then the command succeeds
    And the output contains "matches the package version"

  Scenario: auto-detects npm from package.json, tag matches
    Given a git repository with version "1.2.3" in package.json
    And the tag "v1.2.3" exists locally
    When I run "check" with argument "1.2.3" without specifying a packager
    Then the command succeeds
    And the output contains "matches the package version"
