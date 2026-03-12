from typing import Protocol

from modules.shorter.application.template.dto.result_create_template import (
    ResultCreateTemplateDTO,
)


class CreateTemplateUseCaseProtocol(Protocol):
    def __call__(self) -> ResultCreateTemplateDTO: ...


class CreateTemplateUseCaseImpl:
    def __init__(self): ...

    def __call__(self) -> ResultCreateTemplateDTO: ...
