PACKAGE_TARGET := src/tag_sync

default: help


## ==== Quality Control ================================================================================================

qa: qa/full  ## Shortcut for qa/full

qa/test:  ## Run the tests
	@uv run pytest

qa/types:  ## Run static type checks
	@uv run ty check ${PACKAGE_TARGET} tests

qa/lint:  ## Run linters
	@uv run ruff check ${PACKAGE_TARGET} tests
	@uv run typos ${PACKAGE_TARGET} tests docs/source

qa/full: qa/test qa/lint qa/types  ## Run the full set of quality checks
	@echo "All quality checks pass!"

qa/format:  ## Run code formatter
	@uv run ruff check --select I --fix ${PACKAGE_TARGET} tests
	@uv run ruff format ${PACKAGE_TARGET} tests


## ==== Documentation ==================================================================================================

docs: docs/serve  ## Shortcut for docs/serve

docs/build:  ## Build the documentation
	@uv run zensical build --config-file=docs/mkdocs.yaml

docs/serve:  ## Build the docs and start a local dev server
	@uv run zensical serve --config-file=docs/mkdocs.yaml --dev-addr=localhost:10000


## ==== Other Commands =================================================================================================

publish: _confirm  ## Publish the package by pushing a tag with the current version
	@if [[ "$$(git rev-parse --abbrev-ref HEAD)" != "main" ]]; then \
		echo "You must be on the main branch to publish." && exit 1; \
	fi
	@uv run tag-sync publish v$$(uv version --short)


## ==== Helpers ========================================================================================================

clean:  ## Clean up build artifacts and other junk
	@rm -rf .venv
	@uv run pyclean . --debris
	@rm -rf dist
	@rm -rf .ruff_cache
	@rm -rf .pytest_cache
	@rm -f .coverage*
	@rm -f .junit.xml

help:  ## Show help message
	@awk "$$PRINT_HELP_PREAMBLE" $(MAKEFILE_LIST)


.ONESHELL:
SHELL := /bin/bash
.PHONY: qa qa/test qa/types qa/lint qa/full qa/format docs docs/build docs/serve publish clean help _confirm


RED    := \033[31m
GREEN  := \033[32m
YELLOW := \033[33m
BLUE   := \033[34m
TEAL   := \033[36m
GRAY   := \033[90m
CLEAR  := \033[0m
ITALIC := \033[3m


_confirm:
	@if [[ -z "$(CONFIRM)" ]]; then \
		echo -n "Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]; \
	fi


define PRINT_HELP_PREAMBLE
BEGIN {
	print "Usage: $(YELLOW)make <target>$(CLEAR)"
	print
	print "Targets:"
}
/^## =+ .+( =+)?/ {
	gsub(/^## =+ | =+$$/, "")
	printf "\n$(TEAL)%s$(CLEAR)\n", $$0
}
/^[a-zA-Z0-9_\/-]+:.*?##/ {
	split($$0, a, ":.*?## ")
	printf "  $(GREEN)%-20s$(CLEAR) %s\n", a[1], a[2]
}
endef
export PRINT_HELP_PREAMBLE
