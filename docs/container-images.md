# Container images

The four application images are published to GitHub Container Registry under
`ghcr.io/dinikon/runtime` and linked to
[dinikon/dnk-runtime-core](https://github.com/dinikon/dnk-runtime-core).

| Image | Application | Dockerfile / target | Port |
| --- | --- | --- | --- |
| `ghcr.io/dinikon/runtime/core` | Django Core API | `core/Dockerfile` | 8001 |
| `ghcr.io/dinikon/runtime/runtime` | FastAPI runtime API and workers | `Dockerfile`, `runtime` | 8000 |
| `ghcr.io/dinikon/runtime/frontend-core` | Nuxt Core frontend | `frontends/apps/core/Dockerfile`, `runtime` | 3000 |
| `ghcr.io/dinikon/runtime/frontend-runtime` | Vue runtime console with Nginx | `frontends/Dockerfile`, `runtime` | 80 |

Each release publishes a version tag and `latest`. The initial container release
is `0.0.1`; both `linux/amd64` and `linux/arm64` are built. Container release tags
are independent of the Python/npm workspace package versions.

The [0.0.1 publication record](releases/container-images-0.0.1.json) contains the
verified registry digests, package links and repository associations.

## Build and publish

Run from the repository root with Docker Desktop or a Buildx builder supporting
both target platforms. Builds use the current working tree, including uncommitted
application changes.

Authenticate with a GitHub personal access token (classic) with `write:packages`.
Supply the token through the environment, without saving it in this repository:

```sh
printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u dinikon --password-stdin
```

Build and inspect the images locally first:

```sh
export VERSION=0.0.1
export SOURCE_REVISION="$(git rev-parse HEAD)"
if [ -n "$(git status --porcelain)" ]; then
  export SOURCE_REVISION="${SOURCE_REVISION}-dirty"
fi
docker buildx bake -f docker-bake.hcl --load
```

Publish all four images and both tags:

```sh
docker buildx bake -f docker-bake.hcl --push
```

The registry prefix, version, source URL, revision and platform list can be
overridden through `REGISTRY_PREFIX`, `VERSION`, `SOURCE_URL`, `SOURCE_REVISION`
and `PLATFORMS`. Defaults are in `docker-bake.hcl`.

The source URL is included in both image labels and the multi-platform OCI index
annotations. GHCR needs the index annotation to associate these multi-platform
packages with the repository; keep it when combining or retagging manifests.

Verify the version and `latest` reference the same manifest and include both
platforms:

```sh
for image in core runtime frontend-core frontend-runtime; do
  docker buildx imagetools inspect "ghcr.io/dinikon/runtime/$image:$VERSION"
  docker buildx imagetools inspect "ghcr.io/dinikon/runtime/$image:latest"
done
```

For deployments, use the explicit version tag. New GHCR packages are private by
default, so consumers may need registry credentials. Publishing does not change
package visibility or deploy applications.

## Core gateway

`frontend-core` is the Nuxt application. The existing Compose/Helm topology also
has a separate Nginx gateway (`frontends/apps/core/Dockerfile`, target `gateway`).
That gateway is a fifth image and is not part of these four application packages.
Keep the existing gateway or supply an ingress/proxy that routes public pages to
Nuxt and account/API requests to Django.

See [GitHub Container Registry documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
for authentication and repository metadata through
`org.opencontainers.image.source`.
