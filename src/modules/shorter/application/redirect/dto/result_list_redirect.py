from dataclasses import dataclass

from .redirect import RedirectDTO


@dataclass(frozen=True, slots=True)
class ResultListRedirectDTO:
    items: tuple[RedirectDTO, ...]
