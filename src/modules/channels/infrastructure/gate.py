from hashlib import sha256
from uuid import UUID


def channel_write_lock_key(tenant_id: UUID, channel_id: UUID) -> int:
    """Сериализует изменения доступа одного канала между API и Worker."""
    return int.from_bytes(
        sha256(f"channels:write:{tenant_id}:{channel_id}".encode()).digest()[:8],
        signed=True,
    )
