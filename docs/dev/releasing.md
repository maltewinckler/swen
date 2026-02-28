# Release Process

SWEN uses **git tags** as the version source of truth. A GitHub Release triggers automatic Docker image publishing to Docker Hub.

## Version Scheme

SWEN follows [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

- **PATCH**: Bug fixes, minor improvements (no breaking changes)
- **MINOR**: New features (backwards compatible)
- **MAJOR**: Breaking changes (config format, DB schema, API)

Tags are always prefixed with `v`: `v1.2.3`

## Step-by-Step Release

### 1 · Prepare the Code

```bash
# Make sure you're on main with a clean working tree
git checkout main
git pull origin main
git status  # should be clean
```

### 2 · Verify CI is Green

Check the [GitHub Actions tab](https://github.com/maltewinckler/swen/actions) — all CI jobs must pass on the latest `main` commit before tagging.

### 3 · Create a GitHub Release

1. Go to **GitHub → Releases → Draft a new release**
2. Set the tag to `vX.Y.Z` targeting `main`
3. Write release notes (what changed, migration steps if any)
4. Click **Publish release**

The `docker-publish.yml` workflow fires automatically on publish.

### 4 · Monitor the Build

Watch the **Actions** tab. Three parallel jobs (backend / frontend / ml) should all go green within ~10 minutes.

### 5 · Verify Docker Hub

Check [hub.docker.com/r/maltewin](https://hub.docker.com/r/maltewin) — all three images should have the new version tag and an updated `latest`.

---

## Tags Produced

For `v1.2.3`:

```
maltewin/swen-backend:1.2.3    maltewin/swen-backend:1.2
maltewin/swen-backend:1        maltewin/swen-backend:latest

maltewin/swen-frontend:1.2.3   maltewin/swen-frontend:1.2
maltewin/swen-frontend:1       maltewin/swen-frontend:latest

maltewin/swen-ml:1.2.3         maltewin/swen-ml:1.2
maltewin/swen-ml:1             maltewin/swen-ml:latest
```

---

## `VERSION` Build Arg

Each Dockerfile accepts a `VERSION` build arg that is baked into OCI image labels:

```dockerfile
ARG VERSION=dev
LABEL org.opencontainers.image.version=$VERSION
```

`docker/build-push-action` passes `VERSION=${{ steps.meta.outputs.version }}` automatically.

---

## Updating a Running Deployment

```bash
docker compose pull
docker compose up -d
```

This pulls all three images (backend, frontend, ml) and restarts only the containers whose image changed. The `postgres-data` and `ml-model-cache` volumes are untouched.

---

## Pre-releases

Tag as `v1.2.3-rc1` — `docker/metadata-action` will create:

```
maltewin/swen-backend:1.2.3-rc1
maltewin/swen-backend:latest     ← note: pre-releases still update latest
```

If you don't want pre-releases to update `latest`, set `flavor: latest=false` in the metadata action for RC builds.

---

## Hotfix on a Previous Minor

If `main` has already moved to `v1.3.0` and you need to patch `v1.2.x`:

```bash
git checkout v1.2.0
git checkout -b hotfix/1.2.1
# ... fix ...
git tag v1.2.1
git push origin v1.2.1
```

Then create a GitHub Release from tag `v1.2.1`. Note: `latest` will **not** be updated if `v1.2.1 < v1.3.0` — `docker/metadata-action` only updates `latest` for the highest semver tag.

---

## Required Repository Secrets

| Secret | Value |
|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub username (`maltewin`) |
| `DOCKERHUB_TOKEN` | Docker Hub access token (not your password) |

Set these at **GitHub → Settings → Secrets and variables → Actions**.
