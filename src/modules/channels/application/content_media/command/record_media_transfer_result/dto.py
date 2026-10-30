from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RecordMediaTransferResultResultDTO:
    """Результат record_media_transfer_result без документов хранения."""

    applied: bool
