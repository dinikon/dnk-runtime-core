from dataclasses import dataclass, replace
from datetime import datetime

from src.modules.channels.application.product_representation.contracts import (
    PreparedRepresentation,
)
from src.modules.channels.application.product_representation.port.files import (
    RepresentationFilesPort,
)
from src.modules.channels.application.product_representation.port.rich_text import (
    RepresentationRichTextPort,
)
from src.modules.channels.application.product_representation.service.builder import (
    RepresentationBuilder,
)
from src.modules.channels.application.product_representation.service.reader import (
    RepresentationContext,
)
from src.modules.channels.domain.product_representation.overrides import (
    RepresentationOverridesVO,
    ItemOverridesVO,
    LocalizedOverridesVO,
)
from src.modules.channels.domain.product_representation.policy import (
    RepresentationPolicy,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class PreparedRepresentationDraft:
    """Нормализованное намерение и проверенный результат одной подготовки."""

    overrides: RepresentationOverridesVO
    prepared: PreparedRepresentation
    export_blockers: tuple[str, ...]
    unavailable_files: tuple[EntityIdVO, ...]


class RepresentationDrafts:
    """Координирует очистку текста, Files и общий builder для preview/save/enable."""

    def __init__(
        self,
        *,
        builder: RepresentationBuilder,
        files: RepresentationFilesPort,
        rich_text: RepresentationRichTextPort,
    ) -> None:
        """Получает только Application-порты и сервис подготовки."""
        self._builder = builder
        self._files = files
        self._rich_text = rich_text

    def normalize(
        self, overrides: RepresentationOverridesVO
    ) -> RepresentationOverridesVO:
        """Очищает только явно заданные описания, сохраняя остальные поля."""

        def clean(value: LocalizedOverridesVO) -> LocalizedOverridesVO:
            """Сохраняет None и явную пустую строку при очистке HTML."""
            return replace(
                value,
                body=(
                    self._rich_text.clean(value.body)
                    if value.body is not None
                    else None
                ),
            )

        return RepresentationOverridesVO(
            tuple(clean(value) for value in overrides.common),
            tuple(
                ItemOverridesVO(
                    item.binding_item_id, tuple(clean(value) for value in item.content)
                )
                for item in overrides.items
            ),
        )

    async def prepare(
        self,
        *,
        context: RepresentationContext,
        overrides: RepresentationOverridesVO,
        as_of: datetime,
        locales: tuple[str, ...] | None = None,
        for_update: bool = False,
    ) -> PreparedRepresentationDraft:
        """Собирает текущий результат без сетевых операций и записи состояния."""
        value = self.normalize(overrides)
        RepresentationPolicy.ensure_overrides_scope(
            overrides=value,
            item_ids=tuple(EntityIdVO(item.id) for item in context.binding.items),
            locales=context.locales,
            previous=context.state.overrides,
        )
        prepared = await self._builder.build(
            channel_id=context.channel.id,
            binding=context.binding,
            platform=context.channel.platform_kind,
            config_revision=context.channel.config_revision,
            locales=locales if locales is not None else context.locales,
            as_of=as_of,
            overrides=value,
        )
        file_ids = {identifier.uuid for identifier in value.file_ids()}
        file_ids.update(
            image.file_id.uuid
            for target in prepared.preparation.targets
            for content in target.content
            for image in content.gallery or ()
        )
        unavailable = tuple(
            EntityIdVO(identifier)
            for identifier in await self._files.unavailable(
                tuple(sorted(file_ids)), for_update=for_update
            )
        )
        if unavailable:
            prepared = replace(
                prepared,
                preparation=RepresentationPolicy.with_unavailable_files(
                    preparation=prepared.preparation, unavailable=unavailable
                ),
            )
        channel = context.channel
        blockers = RepresentationPolicy.export_blockers(
            preparation=prepared.preparation,
            mode=context.binding.mode,
            verification_status=channel.verification.status,
            verification_revision=channel.verification.config_revision,
            config_revision=channel.config_revision,
            has_identity=channel.identity is not None,
            unavailable_files=bool(unavailable),
        )
        return PreparedRepresentationDraft(value, prepared, blockers, unavailable)
