"""Общая сборка Cipher для HTTP, worker и CLI."""

from typing import Annotated

from fastapi import Depends

from src.config import dnk_config
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.infrastructure.crypto.fernet_cipher import FernetCipher


def get_cipher() -> Cipher:
    """Собирает адаптер из единственной конфигурации шифрования проекта."""
    key = dnk_config.ENCRYPTION.resolved_key
    return FernetCipher(key.get_secret_value() if key else None)


CipherDep = Annotated[Cipher, Depends(get_cipher)]
