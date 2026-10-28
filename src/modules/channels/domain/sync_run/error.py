"""Предметные ошибки синхронизации публикаций."""

from src.modules.shared.domain.domain_error import DomainError


class SyncRunError(DomainError):
    """Базовая ошибка синхронизации."""


class InvalidSyncRunError(SyncRunError):
    """Состояние запуска или переход противоречит его инвариантам."""


class SyncRunNotFoundError(SyncRunError):
    """Запуск отсутствует в выбранном подключении."""


class SyncNotAvailableError(SyncRunError):
    """Текущее подключение ещё не допускает синхронизацию."""
