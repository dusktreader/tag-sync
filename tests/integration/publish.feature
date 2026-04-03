Feature: publish command

  Background:
    Given a git repository with version "1.2.3" in pyproject.toml

  Scenario: publish a new tag successfully
    When I run "publish" with argument "v1.2.3"
    Then the command succeeds
    And the output contains "published successfully"
    And the tag "v1.2.3" exists locally
    And the tag "v1.2.3" exists on the upstream

  Scenario: publish fails when version does not match
    When I run "publish" with argument "v2.0.0"
    Then the command fails
    And the tag "v2.0.0" does not exist locally

  Scenario: publish fails when tag is already published
    Given the tag "v1.2.3" exists on the upstream
    When I run "publish" with argument "v1.2.3"
    Then the command fails
    And the output contains "already published"

  Scenario: dry run does not create or push a tag
    When I run "publish" with argument "v1.2.3" and flag "--dry-run"
    Then the command succeeds
    And the tag "v1.2.3" does not exist locally

  Scenario: replace an existing tag after confirmation
    Given the tag "v1.2.3" exists locally and on the upstream
    When I run "publish" with argument "v1.2.3" and flag "--replace" confirmed
    Then the command succeeds
    And the tag "v1.2.3" exists locally
    And the tag "v1.2.3" exists on the upstream

  Scenario: replace declined aborts
    Given the tag "v1.2.3" exists locally and on the upstream
    When I run "publish" with argument "v1.2.3" and flag "--replace" declined
    Then the command fails

  Scenario: tag version derived from package version when omitted
    When I run "publish" without a tag argument
    Then the command succeeds
    And the output contains "published successfully"
    And the tag "v1.2.3" exists locally
    And the tag "v1.2.3" exists on the upstream

  Scenario: tag version derived from prerelease package version when omitted
    Given a git repository with version "2.0.0a1" in pyproject.toml
    When I run "publish" without a tag argument
    Then the command succeeds
    And the output contains "published successfully"
    And the tag "v2.0.0-alpha.1" exists locally
    And the tag "v2.0.0-alpha.1" exists on the upstream
