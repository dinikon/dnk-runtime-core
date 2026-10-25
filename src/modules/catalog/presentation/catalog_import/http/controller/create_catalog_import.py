import hashlib
from dataclasses import asdict
from typing import Annotated
from uuid import UUID, uuid5
from urllib.parse import urlsplit
from datetime import UTC, datetime
from fastapi import Header, HTTPException
from src.config import dnk_config
from src.modules.catalog.presentation.catalog_import.depends import (
    CreateCatalogImportHandlerDep,
    ImportTenantDep,
    import_http_error,
)
from src.modules.catalog.presentation.catalog_import.multipart import ImportSourceDep
from src.modules.catalog.presentation.catalog_import.http.response.create_catalog_import import (
    CreateCatalogImportResponse,
)
from src.modules.catalog.application.catalog_import.command.create_catalog_import.command import (
    CreateCatalogImportCommand,
)
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
)
from src.modules.catalog.domain.error import CatalogError
from src.modules.catalog.infrastructure.catalog_import.download import (
    validate_public_url,
)
from src.modules.catalog.infrastructure.catalog_import.repository import (
    SqlAlchemyCatalogImportRepository,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.files.infrastructure.assembly import (
    build_artifact_files_facade,
    get_storage_resolver,
)
from src.modules.files.application.port.storage import (
    StorageUnavailableError,
    StorageConfigurationError,
)
from src.modules.files.domain.error import (
    StorageNotFoundError,
    InvalidStorageStateError,
    InvalidFileError,
)


async def create_catalog_import(
    context: AuthenticatedRequestContextDep,
    tenant: ImportTenantDep,
    payload: ImportSourceDep,
    handler: CreateCatalogImportHandlerDep,
    uow: UoWDep,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=200)],
) -> CreateCatalogImportResponse:
    """Сохраняет источник и создаёт задачу после подтверждения приватного файла."""
    try:
        configuration = ImportConfiguration(
            default_locale=payload.default_locale, timezone=payload.timezone
        )
        file_id: UUID | None = None
        url = validate_public_url(payload.url) if payload.url is not None else None
        digest = hashlib.sha256()
        if payload.file:
            if (
                payload.file.size is None
                or not 0
                < payload.file.size
                <= dnk_config.CATALOG_IMPORT.source_max_bytes
            ):
                raise HTTPException(413, "Недопустимый размер файла.")
            while chunk := payload.file.file.read(65536):
                digest.update(chunk)
            name = (payload.file.filename or "catalog-import").replace(
                "\\", "/"
            ).rsplit("/", 1)[-1][:255] or "catalog-import"
        else:
            digest.update((url or "").encode())
            name = urlsplit(url or "").hostname or "catalog-import"
        digest.update(repr(asdict(configuration)).encode())
        fingerprint = digest.hexdigest()
        repository = SqlAlchemyCatalogImportRepository(uow.session)
        await repository.lock_lane()
        existing = await repository.by_key(idempotency_key)
        if existing:
            if existing.fingerprint != fingerprint:
                raise HTTPException(
                    409, "Idempotency-Key уже использован для другого источника."
                )
            return CreateCatalogImportResponse(
                id=existing.id.uuid, status=existing.status
            )
        if payload.file:
            file_id = uuid5(
                tenant, "catalog-import-source:" + idempotency_key + ":" + fingerprint
            )
            location = await build_artifact_files_facade(uow.session).reserve(
                tenant,
                file_id,
                name,
                "application/octet-stream",
                payload.file.size,
                datetime.now(UTC),
            )
            await uow.commit()
            payload.file.file.seek(0)
            actual = (
                await get_storage_resolver()
                .resolve(location.location)
                .put(
                    location.location,
                    location.key,
                    payload.file.file,
                    payload.file.size,
                    "application/octet-stream",
                )
            )
            await build_artifact_files_facade(uow.session).confirm(file_id, actual)
        assert context.principal is not None
        result = await handler.execute(
            CreateCatalogImportCommand(
                tenant,
                UUID(context.principal.user_id),
                idempotency_key,
                fingerprint,
                name,
                url,
                file_id,
                configuration,
            )
        )
        return CreateCatalogImportResponse(id=result.id, status=result.status)
    except CatalogError as error:
        raise import_http_error(error) from error
    except (StorageUnavailableError, StorageConfigurationError) as error:
        raise HTTPException(503, "Хранилище файлов временно недоступно.") from error
    except (StorageNotFoundError, InvalidStorageStateError) as error:
        raise HTTPException(
            503, "Файловое хранилище рабочего пространства не подготовлено."
        ) from error
    except InvalidFileError as error:
        raise HTTPException(
            422, "Некорректное имя или размер исходного файла."
        ) from error
