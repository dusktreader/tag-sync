# Publishing

This page covers how to set up a GitHub Actions workflow that automatically
publishes your package to a registry whenever a `tag-sync` tag is pushed.

- **Python packages** — publish to [PyPI](https://pypi.org) with `uv publish`
- **npm packages** — publish to [npmjs.com](https://www.npmjs.com) with `npm publish`


## How the workflow fits together

`tag-sync publish` creates and pushes the git tag. GitHub Actions detects that
push and runs the workflow, which:

1. Verifies the pushed tag matches the current version in the manifest using
   `tag-sync check` — a defence-in-depth guard against stale checkouts or
   accidental tag pushes.
2. Builds the package.
3. Publishes to the registry.


## Tag pattern matching

### Trigger filter

The `on.push.tags` filter in the workflow must match whatever pattern
`tag-sync` is configured to produce.

Default pattern (`v{version}`) — matches `v1.2.3`, `v1.2.3-alpha.1`, etc.:

```yaml
on:
  push:
    tags:
      - "v[0-9]+.[0-9]+.[0-9]+*"
```

Custom pattern (e.g. `release/qastg/{version}`) — adjust accordingly:

```yaml
on:
  push:
    tags:
      - "release/qastg/[0-9]+.[0-9]+.[0-9]+*"
```

### Passing the version to `tag-sync check`

`tag-sync check` takes a bare semver. The tag pattern parses the version out of
`${{ github.ref_name }}` automatically, so pass it directly:

```yaml
- name: Verify tag matches package version
  run: uvx tag-sync check ${{ github.ref_name }}
```

If your project uses a custom tag pattern and has a config file
(`.tag-sync.toml`, `pyproject.toml [tool.tag-sync]`, etc.), `tag-sync` reads
the pattern automatically. No extra flags needed.

Without a config file, pass `--tag-pattern` explicitly:

```yaml
- name: Verify tag matches package version
  run: uvx tag-sync check ${{ github.ref_name }} --tag-pattern "release/qastg/{version}"
```


---


## Publishing a Python package to PyPI

### Authentication: OIDC trusted publishing

The recommended approach is **OIDC trusted publishing**. PyPI issues a
short-lived token directly to the workflow at runtime — no API tokens or
secrets need to be stored in GitHub.


#### One-time PyPI setup

1. Go to your PyPI project → **Manage** → **Publishing**.
2. Under *Add a new publisher*, choose **GitHub Actions** and fill in:

    | Field             | Value                             |
    |-------------------|-----------------------------------|
    | Owner             | your GitHub username or org       |
    | Repository        | your repo name                    |
    | Workflow filename | `publish.yml`                     |
    | Environment name  | `pypi` (optional but recommended) |

3. Click **Add**.


#### One-time GitHub setup

In your repository go to **Settings** → **Environments** and create an
environment named `pypi`. You can add protection rules here — for example,
requiring manual approval from a trusted reviewer before each publish run.

----

### Workflow file

Create `.github/workflows/publish.yml`:

```yaml
name: Publish

on:
  push:
    tags:
      - "v[0-9]+.[0-9]+.[0-9]+*"

jobs:
  publish:
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/project/<your-package>/
    permissions:
      id-token: write   # required for OIDC trusted publishing
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true

      - name: Verify tag matches package version
        run: uvx tag-sync check ${{ github.ref_name }}

      - name: Build
        run: uv build

      - name: Publish
        run: uv publish
```


### Running tests before publishing

Gate the publish on a passing test suite with a `needs:` dependency:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
      - run: uv sync --locked
      - run: uv run pytest

  publish:
    needs: test
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/project/<your-package>/
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
      - name: Verify tag matches package version
        run: uvx tag-sync check ${{ github.ref_name }}
      - run: uv build
      - run: uv publish
```


### End-to-end flow

```bash
# 1. Bump the version in pyproject.toml
uv version 1.3.0

# 2. Commit the version bump
git add pyproject.toml uv.lock
git commit -m "bump version to 1.3.0"

# 3. Push the tag — triggers the workflow
tag-sync publish
```


---


## Publishing an npm package to npmjs.com

### Authentication: npm access token

npm does not yet support keyless OIDC publishing, so you need to store an
access token as a GitHub Actions secret.


#### One-time npm setup

1. Log in to [npmjs.com](https://www.npmjs.com) and go to **Access Tokens**.
2. Generate a new **Automation** token (scoped to publish).
3. Copy the token.


#### One-time GitHub setup

In your repository go to **Settings** → **Secrets and variables** →
**Actions** and add a secret named `NPM_TOKEN` with the token value.

----

### Workflow file

Create `.github/workflows/publish.yml`:

```yaml
name: Publish

on:
  push:
    tags:
      - "v[0-9]+.[0-9]+.[0-9]+*"

jobs:
  publish:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "lts/*"
          registry-url: "https://registry.npmjs.org"

      - name: Install dependencies
        run: npm ci

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Verify tag matches package version
        run: uvx tag-sync check ${{ github.ref_name }}

      - name: Publish
        run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

`actions/setup-node` writes an `.npmrc` that injects `NODE_AUTH_TOKEN` as the
registry auth credential, so no manual `.npmrc` configuration is needed.


### Running tests before publishing

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "lts/*"
      - run: npm ci
      - run: npm test

  publish:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "lts/*"
          registry-url: "https://registry.npmjs.org"
      - uses: astral-sh/setup-uv@v7
      - run: npm ci
      - name: Verify tag matches package version
        run: uvx tag-sync check ${{ github.ref_name }}
      - run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```


### End-to-end flow

```bash
# 1. Bump the version in package.json
npm version 1.3.0 --no-git-tag-version

# 2. Commit the version bump
git add package.json
git commit -m "bump version to 1.3.0"

# 3. Push the tag — triggers the workflow
tag-sync publish
```
