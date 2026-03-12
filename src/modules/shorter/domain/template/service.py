from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared import EntityIdVO
from src.modules.shorter.domain.errors import (
    LinkCodeAlreadyExistsError,
    LinkCodeGenerationAttemptsExceededError,
)
from src.modules.shorter.domain.link.entity import LinkEntity
from src.modules.shorter.domain.link.port import (
    LinkCodeGeneratorPort,
    LinkCodeUniquenessCheckerPort,
)
from src.modules.shorter.domain.template.entity import TemplateEntity
from src.modules.shorter.domain.template.value_object import (
    TemplateEntityTypeVO,
    TemplateTargetModuleTypeVO,
)


@dataclass(frozen=True, slots=True)
class TemplateCreateResult:
    template: TemplateEntity
    link: LinkEntity


class TemplateCreateService:
    def __init__(
        self,
        *,
        link_uniqueness_checker: LinkCodeUniquenessCheckerPort,
        code_generator: LinkCodeGeneratorPort,
        generation_attempts_limit: int = 1024,
    ):
        if generation_attempts_limit < 1:
            raise ValueError("generation_attempts_limit must be greater than zero")
        self._link_uniqueness_checker = link_uniqueness_checker
        self._code_generator = code_generator
        self._generation_attempts_limit = generation_attempts_limit

    def create(
        self,
        *,
        created_by: EntityIdVO,
        domain_id: EntityIdVO,
        target_module: TemplateTargetModuleTypeVO,
        target_entity: TemplateEntityTypeVO,
        target_entity_id: EntityIdVO,
        code: str | None = None,
    ) -> TemplateCreateResult:
        resolved_code = self._resolve_code(
            domain_id=domain_id,
            raw_code=code,
        )
        link = LinkEntity.create(
            domain_id=domain_id,
            code=resolved_code,
        )
        template = TemplateEntity.create(
            user_id=created_by,
            default_code=link.id,
            target_module=target_module,
            target_entity=target_entity,
            target_entity_id=target_entity_id,
        )
        return TemplateCreateResult(template=template, link=link)

    def _resolve_code(self, *, domain_id: EntityIdVO, raw_code: str | None) -> str:
        code = raw_code.strip() if raw_code is not None else ""
        if code:
            self._ensure_unique_code(domain_id=domain_id, code=code)
            return code
        return self._generate_unique_code(domain_id=domain_id)

    def _generate_unique_code(self, *, domain_id: EntityIdVO) -> str:
        for _ in range(self._generation_attempts_limit):
            generated_code = self._code_generator.generate(length=8)
            if not self._link_uniqueness_checker.exists_by_domain_and_code(
                domain_id=domain_id,
                code=generated_code,
            ):
                return generated_code
        raise LinkCodeGenerationAttemptsExceededError(
            domain_id=str(domain_id),
            attempts=self._generation_attempts_limit,
        )

    def _ensure_unique_code(self, *, domain_id: EntityIdVO, code: str) -> None:
        if self._link_uniqueness_checker.exists_by_domain_and_code(
            domain_id=domain_id,
            code=code,
        ):
            raise LinkCodeAlreadyExistsError(
                domain_id=str(domain_id),
                code=code,
            )


__all__ = [
    "TemplateCreateResult",
    "TemplateCreateService",
]
