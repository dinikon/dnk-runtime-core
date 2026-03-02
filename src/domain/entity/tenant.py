from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Tenant:
    id: str
    name: str
    encrypt_public_key: str | None
    status: str
    custom_config: str | None
    created_at: datetime
    updated_at: datetime
