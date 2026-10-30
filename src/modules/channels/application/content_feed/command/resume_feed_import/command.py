from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResumeFeedImportCommand:
    """Намерение сценария resume_feed_import с обоими expected-revision токенами."""

    channel_id: UUID
    feed_id: UUID
    actor_id: UUID
    expected_revision: int
    expected_delivery_revision: int
