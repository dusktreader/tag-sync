Feature: verify command (auto-detect packager)

  Scenario: auto-detects uv from pyproject.toml, version is published
    Given a git repository with version "2.0.0" in pyproject.toml
    And the tag "v2.0.0" exists on the upstream
    When I run "verify" without specifying a packager
    Then the command succeeds
    And the output contains "already published"
    And the output contains "v2.0.0"

  Scenario: auto-detects npm from package.json, version not published
    Given a git repository with version "1.0.0-alpha.1" in package.json
    And no tags exist on the upstream
    When I run "verify" without specifying a packager
    Then the command succeeds
    And the output contains "not been published"
    And the output contains "v1.0.0-alpha.1"
