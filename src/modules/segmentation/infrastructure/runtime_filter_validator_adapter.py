from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.modules.runtime_data.application.query.filter_dsl.parser import (
    FilterDslParser,
)
from src.modules.runtime_data.application.query.filter_dsl.semantic_validator import (
    FilterSemanticValidator,
)
from src.modules.runtime_data.domain.error import RuntimeDataFilterError
from src.modules.schema_registry.domain.error import RuntimeObjectNotFoundError
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.segmentation.application.segment_version.dsl.error import (
    SegmentVersionDslInvalidRuleError,
    SegmentVersionDslValidationError,
)
from src.modules.shared import EntityIdVO


class RuntimeFilterValidatorAdapter:
    """Adapter that validates segment rule filters with runtime_data DSL."""

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        parser: FilterDslParser | None = None,
        semantic_validator: FilterSemanticValidator | None = None,
    ) -> None:
        self._runtime_object_resolver = runtime_object_resolver
        self._parser = parser or FilterDslParser()
        self._semantic_validator = semantic_validator or FilterSemanticValidator()

    async def validate_filter(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
        filter_config: Mapping[str, Any],
        path: str,
    ) -> None:
        try:
            descriptor = await self._runtime_object_resolver.resolve(
                tenant_id=tenant_id,
                object_name=object_name,
            )
        except RuntimeObjectNotFoundError as exc:
            raise SegmentVersionDslInvalidRuleError(
                f"Unknown filter object '{object_name}'.",
                path=path,
            ) from exc

        try:
            filter_ast = self._parser.parse(filter_config)
            self._semantic_validator.validate(
                descriptor=descriptor,
                filter_ast=filter_ast,
            )
        except RuntimeDataFilterError as exc:
            raise SegmentVersionDslValidationError(
                str(exc),
                path=path,
            ) from exc


__all__ = ["RuntimeFilterValidatorAdapter"]
