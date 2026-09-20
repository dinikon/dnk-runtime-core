from contextlib import aclosing
from src.modules.price_lists.application.sync_run.ports import (
    SourceFetcher,
    SourceParserPort,
    SourceCipher,
)
from src.modules.price_lists.application.sync_run.options import ImportOptions
from src.modules.price_lists.application.price_list.dto.action_dto import (
    PreviewDTO,
    PreviewRowDTO,
)
from src.modules.price_lists.domain.price_list.value_object.configuration import (
    SourceConfigurationVO,
    MappingConfigurationVO,
)
from src.modules.price_lists.domain.price_list.value_object.source_url import (
    SourceUrlVO,
)
from src.modules.price_lists.domain.price_list.preset import prom_xml_config
from src.modules.price_lists.domain.price_list.error import MappingValidationError


class SourcePreview:
    """Общий ограниченный preview для просмотра и проверки mapping."""

    def __init__(
        self,
        fetcher: SourceFetcher,
        parser: SourceParserPort,
        cipher: SourceCipher,
        options: ImportOptions,
    ):
        self.fetcher = fetcher
        self.parser = parser
        self.cipher = cipher
        self.options = options

    def candidate(self, price, changes):
        """Разрешает кандидат настроек без сохранения секретного URL в DTO."""
        resolved = {
            name: changes.get(name, getattr(price, name))
            for name in (
                "source_format",
                "source_preset",
                "source_config",
                "mapping_config",
            )
        }
        resolved["source_url"] = SourceUrlVO(
            changes.get("source_url") or self.cipher.decrypt(price.source_url_secret)
        ).value
        if resolved["source_preset"] == "prom_xml":
            if resolved["source_format"] != "xml":
                raise MappingValidationError("Prom preset requires XML format.")
            source, mapping = prom_xml_config()
            resolved["source_config"] = source | resolved["source_config"]
            resolved["mapping_config"] = resolved["mapping_config"] or mapping
        elif resolved["source_preset"] is not None:
            raise MappingValidationError("Unknown source preset.")
        SourceConfigurationVO(resolved["source_format"], resolved["source_config"])
        if resolved["mapping_config"]:
            MappingConfigurationVO(resolved["mapping_config"])
        return resolved

    async def inspect(self, candidate, *, limit=20, validate=False):
        """Скачивает sample через те же async adapters, что импорт."""
        rows = []
        async with self.fetcher.open(candidate["source_url"]) as source:
            inspection = await self.parser.inspect_source(
                source.path, candidate["source_format"], candidate["source_config"]
            )
            if candidate["mapping_config"]:
                async with aclosing(
                    self.parser.batches(
                        source.path,
                        candidate["source_format"],
                        candidate["source_config"],
                        candidate["mapping_config"],
                        limit=limit,
                    )
                ) as batches:
                    async for batch in batches:
                        rows.extend(batch)
            if validate:
                rejected = sum(bool(row.errors) for row in rows)
                external_ids = [
                    str(row.normalized["external_id"])
                    for row in rows
                    if row.normalized.get("external_id") not in (None, "")
                ]
                if (
                    not rows
                    or rejected == len(rows)
                    or rejected > len(rows) * self.options.max_error_ratio
                ):
                    raise MappingValidationError(
                        "Mapping preview validation threshold exceeded."
                    )
                if len(external_ids) != len(set(external_ids)):
                    raise MappingValidationError(
                        "Mapping preview contains duplicate external_id values."
                    )
            return PreviewDTO(
                candidate["source_format"],
                source.content_type,
                source.size,
                source.checksum,
                tuple(
                    PreviewRowDTO(row.row_number, row.normalized, row.errors)
                    for row in rows
                ),
                inspection.sheets,
                inspection.columns,
                inspection.paths,
            )


__all__ = ["SourcePreview"]
