# CI/CD implementation plan

## Goal

Set up a staged CI/CD process for `dnk-runtime-core` from development branches to production publication.

Target behavior:

- `feature/*` and `bug-fix/*`: run CI checks only.
- `develop`: run CI checks and build a development Docker image.
- `pre-release`: run CI checks, build an image, deploy to the test Kubernetes environment through ArgoCD and Helm.
- `release`: run CI checks, create a semantic version tag, publish a GitHub Release, build production images, deploy to production through ArgoCD and Helm.
- `main`: keep stable released state. It should be updated after successful production release.

## Current project notes

- The project already has `Dockerfile`, `uv.lock`, `pyproject.toml`, and `test/`.
- Tests are run with:

```bash
uv run python -m unittest discover -s test -p "test_*.py" -v
```

- Compile smoke check:

```bash
uv run python -m compileall src
```

- `pyproject.toml` currently requires `Python ==3.13.9`, but `Dockerfile` uses `python:3.12-slim-bookworm`.
  This must be aligned before Docker image build becomes a required CI gate.
- Helm charts and ArgoCD Applications are implemented under `helm/dnk-runtime-core` and `deploy/argocd`. The current installation and migration contract is documented in [the Helm guide](../../helm/README.md); the pipeline sketches below are historical planning context.

## Branch strategy

Use persistent branches:

```text
main
develop
pre-release
release
```

Use branch prefixes for work branches:

```text
feature/<task-or-ticket>
bug-fix/<task-or-ticket>
```

Do not use long-lived `feature` and `bug-fix` branches unless there is a separate operational reason.
They are better as prefixes because each task gets isolated CI status and a focused PR.

Branch flow:

```text
feature/* or bug-fix/*
  -> PR to develop
  -> merge develop to pre-release
  -> merge pre-release to release
  -> release automation publishes production
  -> merge release back to main and develop
```

## Required GitHub settings

Branch protection:

```text
develop:
  require pull request
  require CI checks

pre-release:
  require pull request
  require CI checks

release:
  require pull request
  require CI checks
  require production environment approval before deploy-prod

main:
  require pull request
  require CI checks
  no direct pushes
```

GitHub environments:

```text
test:
  used by pre-release deploy

production:
  used by release deploy
  requires manual approval
```

Secrets and variables:

```text
REGISTRY=ghcr.io
IMAGE_NAME=dnk-runtime-core
GITOPS_REPO=<org>/<gitops-repo>
GITOPS_TOKEN=<token with write access to GitOps repo>
```

Optional only if GitHub Actions must force ArgoCD sync:

```text
ARGOCD_SERVER
ARGOCD_AUTH_TOKEN
```

Preferred deployment model: GitHub Actions updates the GitOps repository with a new Helm image tag, and ArgoCD syncs Kubernetes from Git. Avoid storing direct Kubernetes credentials in GitHub Actions.

## Task 1. Add CI for development branches

Purpose: make every `feature/*`, `bug-fix/*`, and `develop` change testable before any image build or deployment logic exists.

Files to add:

```text
.github/workflows/ci.yml
```

Workflow pseudocode:

```yaml
name: ci

on:
  pull_request:
    branches:
      - develop
      - pre-release
      - release
      - main
  push:
    branches:
      - develop
      - "feature/**"
      - "bug-fix/**"

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Install dependencies
        run: uv sync --frozen

      - name: Compile source
        run: uv run python -m compileall src

      - name: Check formatting
        run: uv run black --check src test

      - name: Run tests
        run: uv run python -m unittest discover -s test -p "test_*.py" -v
```

Immediate test:

```bash
uv run python -m compileall src
uv run python -m unittest discover -s test -p "test_*.py" -v
```

GitHub test:

```text
1. Create feature/ci-smoke.
2. Push a small documentation-only change.
3. Open PR to develop.
4. Verify CI check appears and passes.
```

Acceptance criteria:

```text
CI is required before merge to develop.
Failed tests block PR merge.
No Docker registry or Kubernetes access is required at this stage.
```

## Task 2. Align Python runtime for CI and Docker

Purpose: make local install, CI test, and Docker build use the same Python version.

Files to update:

```text
Dockerfile
pyproject.toml, only if the project decides to change the required Python version
```

Recommended option:

```dockerfile
FROM python:3.13-slim-bookworm AS runtime
```

Immediate test:

```bash
docker build -t dnk-runtime-core:local .
docker run --rm dnk-runtime-core:local python --version
```

Expected result:

```text
The image Python version satisfies pyproject.toml.
The image build finishes with uv sync --frozen.
```

Acceptance criteria:

```text
Docker image can be built from the current lock file.
CI Python and container Python are compatible.
```

## Task 3. Build and publish development images from develop

Purpose: prove container publishing before adding deployment.

Update:

```text
.github/workflows/ci.yml
```

Add job pseudocode:

```yaml
  build-dev-image:
    needs: test
    if: github.event_name == 'push' && github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/dnk-runtime-core:develop
            ghcr.io/${{ github.repository_owner }}/dnk-runtime-core:dev-${{ github.sha }}
```

Immediate test:

```text
1. Merge a PR into develop.
2. Check GitHub Actions build-dev-image job.
3. Check GHCR package contains tags develop and dev-<sha>.
```

Optional local test:

```bash
docker pull ghcr.io/<org>/dnk-runtime-core:develop
docker run --rm -p 8000:8000 ghcr.io/<org>/dnk-runtime-core:develop
```

Acceptance criteria:

```text
Development image is published only after CI passes.
Feature and bug-fix branches do not publish images.
```

## Task 4. Create base branches and protection rules

Purpose: lock the workflow before deployment automation is enabled.

Commands:

```bash
git fetch origin

git checkout main
git pull origin main

git checkout -b develop
git push -u origin develop

git checkout main
git checkout -b pre-release
git push -u origin pre-release

git checkout main
git checkout -b release
git push -u origin release
```

If branches already exist, only verify they are up to date.

Immediate test:

```text
1. Try to push directly to protected develop.
2. Confirm GitHub rejects direct push or requires PR.
3. Open a PR from feature/* to develop and confirm required CI appears.
```

Acceptance criteria:

```text
All control branches exist.
Direct pushes are blocked where required.
Required CI checks are attached to protected branches.
```

## Task 5. Add Helm chart for the application

Purpose: make the service deployable in Kubernetes before adding ArgoCD automation.

Files to add:

```text
helm/dnk-runtime-core/Chart.yaml
helm/dnk-runtime-core/values.yaml
helm/dnk-runtime-core/values-test.yaml
helm/dnk-runtime-core/values-prod.yaml
helm/dnk-runtime-core/templates/deployment.yaml
helm/dnk-runtime-core/templates/service.yaml
helm/dnk-runtime-core/templates/ingress.yaml
helm/dnk-runtime-core/templates/configmap.yaml
```

Base values pseudocode:

```yaml
image:
  repository: ghcr.io/<org>/dnk-runtime-core
  tag: develop
  pullPolicy: IfNotPresent

replicaCount: 1

service:
  type: ClusterIP
  port: 8000

env:
  APP_ENV: default

resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

Test values pseudocode:

```yaml
image:
  tag: pre-placeholder

env:
  APP_ENV: test

replicaCount: 1
```

Production values pseudocode:

```yaml
image:
  tag: v0.1.0

env:
  APP_ENV: production

replicaCount: 3
```

Immediate test:

```bash
helm lint helm/dnk-runtime-core
helm template dnk-runtime-core helm/dnk-runtime-core -f helm/dnk-runtime-core/values-test.yaml
helm template dnk-runtime-core helm/dnk-runtime-core -f helm/dnk-runtime-core/values-prod.yaml
```

Acceptance criteria:

```text
helm lint passes.
helm template renders Deployment, Service, ConfigMap and optional Ingress.
The rendered Deployment contains the expected image repository and tag.
```

## Task 6. Add Helm validation to CI

Purpose: prevent broken Kubernetes manifests from reaching `pre-release` or `release`.

Update:

```text
.github/workflows/ci.yml
```

Job pseudocode:

```yaml
  helm:
    needs: test
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: azure/setup-helm@v4

      - name: Helm lint
        run: helm lint helm/dnk-runtime-core

      - name: Render test manifests
        run: helm template dnk-runtime-core helm/dnk-runtime-core -f helm/dnk-runtime-core/values-test.yaml

      - name: Render prod manifests
        run: helm template dnk-runtime-core helm/dnk-runtime-core -f helm/dnk-runtime-core/values-prod.yaml
```

Immediate test:

```text
1. Open PR with a valid Helm chart.
2. Confirm helm job passes.
3. Break a template locally or in a test branch.
4. Confirm helm job fails.
```

Acceptance criteria:

```text
Broken Helm chart blocks merge.
CI validates both test and production values.
```

## Task 7. Prepare GitOps repository structure

Purpose: make ArgoCD deploy from Git state, not from direct CI access to Kubernetes.

Recommended GitOps repository layout:

```text
environments/
  test/
    dnk-runtime-core/
      Chart.yaml or chart reference
      values.yaml
  prod/
    dnk-runtime-core/
      Chart.yaml or chart reference
      values.yaml
argocd/
  applications/
    dnk-runtime-core-test.yaml
    dnk-runtime-core-prod.yaml
```

Test environment values pseudocode:

```yaml
image:
  repository: ghcr.io/<org>/dnk-runtime-core
  tag: pre-placeholder
```

Production environment values pseudocode:

```yaml
image:
  repository: ghcr.io/<org>/dnk-runtime-core
  tag: v0.1.0
```

ArgoCD test application pseudocode:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: dnk-runtime-core-test
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/<org>/<gitops-repo>.git
    targetRevision: main
    path: environments/test/dnk-runtime-core
  destination:
    server: https://kubernetes.default.svc
    namespace: dnk-test
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

ArgoCD production application pseudocode:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: dnk-runtime-core-prod
  namespace: argocd
spec:
  project: production
  source:
    repoURL: https://github.com/<org>/<gitops-repo>.git
    targetRevision: main
    path: environments/prod/dnk-runtime-core
  destination:
    server: https://kubernetes.default.svc
    namespace: dnk-prod
  syncPolicy:
    automated:
      prune: false
      selfHeal: true
```

Immediate test:

```text
1. Commit GitOps test application.
2. Open ArgoCD UI.
3. Confirm dnk-runtime-core-test appears.
4. Confirm rendered manifests are visible.
```

Acceptance criteria:

```text
ArgoCD can read GitOps repo.
Test application can sync into dnk-test namespace.
Production application exists but requires controlled sync/approval policy.
```

## Task 8. Add pre-release deploy to test environment

Purpose: make `pre-release` automatically deploy to test after CI passes.

Files to add or update:

```text
.github/workflows/pre-release.yml
```

Workflow pseudocode:

```yaml
name: pre-release

on:
  push:
    branches:
      - pre-release

permissions:
  contents: read
  packages: write

jobs:
  test:
    uses: ./.github/workflows/ci.yml

  build-image:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - checkout
      - login to ghcr.io
      - build and push:
          tags:
            - ghcr.io/<org>/dnk-runtime-core:pre-release
            - ghcr.io/<org>/dnk-runtime-core:pre-${GITHUB_SHA}

  deploy-test:
    needs: build-image
    environment: test
    runs-on: ubuntu-latest
    steps:
      - checkout GitOps repo using GITOPS_TOKEN
      - update environments/test/dnk-runtime-core/values.yaml:
          image.tag: pre-${GITHUB_SHA}
      - commit:
          message: "deploy(test): dnk-runtime-core pre-${GITHUB_SHA}"
      - push to GitOps main
      - ArgoCD auto-sync deploys the new image
```

Immediate test:

```text
1. Merge develop into pre-release.
2. Confirm pre-release workflow passes.
3. Confirm GHCR contains pre-release and pre-<sha> tags.
4. Confirm GitOps test values.yaml was updated.
5. Confirm ArgoCD synced dnk-runtime-core-test.
6. Confirm Kubernetes Deployment uses image tag pre-<sha>.
```

Acceptance criteria:

```text
Every push to pre-release produces a test deployment.
Failed CI prevents image publishing and deployment.
GitOps repo contains a traceable deploy commit.
```

## Task 9. Configure automatic semantic versioning

Purpose: make release tags deterministic and generated from commit history.

Use Conventional Commits:

```text
fix: correct tenant schema bootstrap
feat: add provider connector import
feat!: change runtime schema contract
```

Recommended `pyproject.toml` config pseudocode:

```toml
[tool.commitizen]
name = "cz_conventional_commits"
tag_format = "v$version"
version_scheme = "semver"
version_provider = "pep621"
update_changelog_on_bump = true
major_version_zero = true
```

Release version rules:

```text
fix      -> patch
feat     -> minor
breaking -> major
```

Immediate test:

```bash
uv run cz check --rev-range origin/release..HEAD
uv run cz bump --dry-run
```

GitHub test:

```text
1. Create test branch from release.
2. Add commits with fix: and feat: messages.
3. Run release workflow in dry-run mode if configured.
4. Confirm expected next version.
```

Acceptance criteria:

```text
Invalid release commit messages are rejected.
Next version can be calculated without manual editing.
Version source of truth is pyproject.toml.
Tags use vX.Y.Z format.
```

## Task 10. Add release workflow for GitHub Release and production image

Purpose: make `release` publish an immutable application release.

Files to add:

```text
.github/workflows/release.yml
```

Workflow pseudocode:

```yaml
name: release

on:
  push:
    branches:
      - release

permissions:
  contents: write
  packages: write

concurrency:
  group: release
  cancel-in-progress: false

jobs:
  test:
    run: same checks as ci

  version:
    needs: test
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
      tag: ${{ steps.version.outputs.tag }}

    steps:
      - checkout with fetch-depth 0
      - setup python and uv
      - uv sync --frozen
      - check conventional commits
      - run:
          uv run cz bump --yes --changelog
      - read version from pyproject.toml
      - commit:
          message: "chore(release): vX.Y.Z"
      - tag:
          name: vX.Y.Z
      - push release commit and tag

  build-prod-image:
    needs: version
    runs-on: ubuntu-latest
    steps:
      - checkout release tag
      - login to ghcr.io
      - build and push:
          tags:
            - ghcr.io/<org>/dnk-runtime-core:vX.Y.Z
            - ghcr.io/<org>/dnk-runtime-core:latest
            - ghcr.io/<org>/dnk-runtime-core:${GITHUB_SHA}

  github-release:
    needs:
      - version
      - build-prod-image
    runs-on: ubuntu-latest
    steps:
      - create GitHub Release:
          tag: vX.Y.Z
          title: vX.Y.Z
          notes: changelog for vX.Y.Z
```

Immediate test:

```text
1. Push to release from a controlled test branch or test repo first.
2. Confirm release workflow calculates next version.
3. Confirm tag vX.Y.Z exists.
4. Confirm GitHub Release exists.
5. Confirm GHCR contains vX.Y.Z and latest image tags.
```

Acceptance criteria:

```text
Release tag is immutable.
GitHub Release is created automatically.
Production image is published only after tests pass.
```

## Task 11. Add production deployment through ArgoCD and Helm

Purpose: deploy only versioned release images to production.

Update:

```text
.github/workflows/release.yml
```

Add deploy job pseudocode:

```yaml
  deploy-prod:
    needs:
      - version
      - build-prod-image
      - github-release
    environment: production
    runs-on: ubuntu-latest

    steps:
      - checkout GitOps repo using GITOPS_TOKEN
      - update environments/prod/dnk-runtime-core/values.yaml:
          image.tag: vX.Y.Z
      - commit:
          message: "deploy(prod): dnk-runtime-core vX.Y.Z"
      - push to GitOps main
      - ArgoCD syncs production from GitOps repo
```

Production safeguards:

```text
Use GitHub production environment approval.
Use ArgoCD project restrictions for production.
Disable automated prune in production unless the team explicitly accepts it.
Deploy only immutable SemVer tags, not latest.
```

Immediate test:

```text
1. Approve production environment job in GitHub Actions.
2. Confirm GitOps prod values.yaml changed to vX.Y.Z.
3. Confirm ArgoCD dnk-runtime-core-prod syncs successfully.
4. Confirm Kubernetes Deployment image is ghcr.io/<org>/dnk-runtime-core:vX.Y.Z.
5. Confirm application health endpoint or docs endpoint responds.
```

Acceptance criteria:

```text
Production deploy cannot happen before GitHub Release and production image are published.
Production deploy has a GitOps commit trail.
Rollback can be done by reverting the GitOps image tag commit.
```

## Task 12. Add post-release synchronization

Purpose: keep `main` and `develop` aligned with released code and version bump.

Options:

```text
Manual:
  PR release -> main
  PR release -> develop

Automated:
  workflow opens PRs after successful production deploy
```

Recommended first implementation:

```text
Use manual PRs until the release flow is stable.
```

Immediate test:

```text
1. After production deploy, open PR from release to main.
2. Confirm CI passes.
3. Merge to main.
4. Open PR from release to develop.
5. Confirm CI passes.
6. Merge to develop.
```

Acceptance criteria:

```text
main contains the released commit and tag history.
develop contains the released version bump and changelog.
Next release starts from a consistent version state.
```

## Task 13. Add rollback procedure

Purpose: make production recovery explicit before relying on automated deploys.

Rollback through GitOps:

```text
1. Find previous stable image tag, for example v0.1.4.
2. Revert the GitOps commit that changed prod image tag to v0.1.5.
3. Push revert commit.
4. ArgoCD syncs production back to v0.1.4.
```

Emergency rollback through ArgoCD UI:

```text
1. Open dnk-runtime-core-prod application.
2. Select previous synced revision.
3. Roll back.
4. Follow up by committing the same target state to GitOps.
```

Immediate test:

```text
1. Run rollback drill in test environment.
2. Deploy pre-<new-sha>.
3. Revert GitOps test image tag to pre-<old-sha>.
4. Confirm ArgoCD returns the test deployment to the old image.
```

Acceptance criteria:

```text
Team can roll back without editing Kubernetes resources manually.
Rollback action leaves a Git history trail.
```

## Final CI/CD path

Expected final sequence:

```text
feature/task
  -> CI
  -> PR to develop

develop
  -> CI
  -> build ghcr.io/<org>/dnk-runtime-core:develop
  -> build ghcr.io/<org>/dnk-runtime-core:dev-<sha>

pre-release
  -> CI
  -> build ghcr.io/<org>/dnk-runtime-core:pre-release
  -> build ghcr.io/<org>/dnk-runtime-core:pre-<sha>
  -> update GitOps test values
  -> ArgoCD deploys test

release
  -> CI
  -> calculate version
  -> create tag vX.Y.Z
  -> create GitHub Release
  -> build ghcr.io/<org>/dnk-runtime-core:vX.Y.Z
  -> build ghcr.io/<org>/dnk-runtime-core:latest
  -> update GitOps prod values
  -> ArgoCD deploys production

main
  -> receives released state from release after production deploy
```

## Definition of done

The CI/CD setup is complete when:

```text
1. PRs to develop are blocked by failing tests.
2. Push to develop publishes a development image.
3. Push to pre-release deploys to test through ArgoCD.
4. Push to release creates SemVer tag and GitHub Release.
5. Release workflow publishes immutable production image tags.
6. Production deploy uses GitHub environment approval.
7. Production deploy updates GitOps repo and ArgoCD syncs from Git.
8. Rollback is tested in the test environment.
9. main and develop are synchronized after production release.
```
