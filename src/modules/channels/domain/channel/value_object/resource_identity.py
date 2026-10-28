"""Устойчивый идентификатор магазина в пространстве платформы."""

from dataclasses import dataclass

from src.modules.channels.domain.channel.error import InvalidResourceIdentityError


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourceIdentityVO:
    """Описывает поддерживаемый ключ внешнего магазина."""

    namespace: str
    key: str

    def __post_init__(self) -> None:
        """Проверяет обязательность и допустимый размер идентификатора."""
        if (
            not isinstance(self.namespace, str)
            or not isinstance(self.key, str)
            or not self.namespace
            or len(self.namespace.encode()) > 100
            or not self.key
            or len(self.key.encode()) > 1024
        ):
            raise InvalidResourceIdentityError(
                "Не удалось определить идентификатор магазина."
            )
