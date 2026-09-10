# Сборка образов Runtime

Адреса опубликованных образов сохранены при разделении репозиториев.
Этот репозиторий собирает только принадлежащие ему приложения:

| Образ | Назначение |
| --- | --- |
| `ghcr.io/dinikon/runtime/runtime` | FastAPI API и workers |
| `ghcr.io/dinikon/runtime/frontend-runtime` | Vue Console / Nginx |

## Проверка и сборка

Из корня текущего репозитория:

```sh
docker buildx bake -f docker-bake.hcl --print
VERSION=0.1.0 IMAGE_TAG=local PLATFORMS=linux/arm64 docker buildx bake -f docker-bake.hcl --load
```

Для linux/amd64 используйте соответствующее значение PLATFORMS. По умолчанию Bake
поддерживает linux/amd64 и linux/arm64; при multi-platform используйте экспорт в registry
или cache, а не single-platform Docker image store. VERSION образа независим от версии chart.

`REGISTRY_PREFIX`, `VERSION`, `IMAGE_TAG`, `SOURCE_URL`, `SOURCE_REVISION`, `PLATFORMS`
задаются явно при необходимости. Source label/annotation соответствует текущему репозиторию.
`VERSION` задаёт метаданные версии, `IMAGE_TAG` — тег образа (по умолчанию `local`).
Тег `latest` автоматически не создаётся.

## Публикация

После проверки сборки и входа в GHCR с правом записи:

```sh
VERSION=0.1.0 IMAGE_TAG=manual-example-unique SOURCE_REVISION="$(git rev-parse HEAD)" docker buildx bake -f docker-bake.hcl --push
```

Для deployment закрепляйте версию или digest, а не latest. Эта ручная публикация не запускает deployment;
используйте новый уникальный тег и не перезаписывайте версии, принадлежащие CI/CD.
Штатный процесс выпуска образов и OCI Helm-пакета описан в [CI/CD](plan/ci-cd.md).
Первоначальные digests и прежняя привязка образов к runtime сохранены в
[историческом release record](releases/container-images-0.0.1.json).
При публикации Core из нового репозитория предоставьте ему доступ к существующим GHCR-пакетам.
