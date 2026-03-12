from __future__ import annotations

from modules.shared import EntityIdVO
from modules.shorter.application.template.command.create_template import (
    CreateTemplateCommand,
)
from modules.shorter.application.template.result.create_template import (
    CreateTemplateResult,
)
from modules.shorter.domain import (
    LinkEntity,
    TemplateEntity,
    LinkCodeGenerationAttemptsExceededError,
    LinkCodeAlreadyExistsError,
)
from modules.shorter.domain.link.port.link_code_uniq_checker import (
    LinkCodeUniquenessCheckerPort,
)
from modules.shorter.infrastructure.infrastructure.services.link_code_generator import (
    LinkCodeGeneratorService,
)


class TemplateCreateService:
    def __init__(
        self,
        link_uniqueness_checker: LinkCodeUniquenessCheckerPort,
        code_generator: LinkCodeGeneratorService | None = None,
        generation_attempts_limit: int = 1024,
    ):
        self._link_uniqueness_checker = link_uniqueness_checker
        self._code_generator = code_generator or LinkCodeGeneratorService()
        self._generation_attempts_limit = generation_attempts_limit

    def create(self, command: CreateTemplateCommand) -> CreateTemplateResult:
        code = self._resolve_code(
            domain_id=command.domain_id,
            raw_code=command.code,
        )
        link = LinkEntity.create(
            domain_id=command.domain_id,
            code=code,
        )
        template = TemplateEntity.create(
            user_id=command.created_by,
            default_code=link.id,
            target_module=command.target_module,
            target_entity=command.target_entity,
            target_entity_id=command.target_entity_id,
        )
        return CreateTemplateResult(template=template, link=link)

    def _resolve_code(self, *, domain_id: EntityIdVO, raw_code: str | None) -> str:
        code = raw_code.strip() if raw_code is not None else ""
        if code:
            self._ensure_unique_code(domain_id=domain_id, code=code)
            return code
        return self._generate_unique_code(domain_id=domain_id)

    def _generate_unique_code(self, *, domain_id: EntityIdVO) -> str:
        for _ in range(self._generation_attempts_limit):
            code = self._code_generator.generate_8()
            if not self._link_uniqueness_checker.exists_by_domain_and_code(
                domain_id=domain_id,
                code=code,
            ):
                return code
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
