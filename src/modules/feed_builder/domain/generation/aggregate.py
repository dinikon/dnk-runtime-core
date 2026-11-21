from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.feed_builder.domain.feed.policy.schema_structure import (
    FeedSchemaStructurePolicy,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.generation.entity.feed_artifact import FeedArtifact
from src.modules.feed_builder.domain.generation.enum.generation_status import (
    GenerationStatus,
)
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError
from src.modules.feed_builder.domain.generation.value_object.feed_generation_id import (
    FeedGenerationIdVO,
)
from src.modules.feed_builder.domain.generation.value_object.generation_attempt import (
    GenerationAttemptVO,
)
from src.modules.feed_builder.domain.generation.value_object.generation_calculation_context import (
    GenerationCalculationContextVO,
)
from src.modules.feed_builder.domain.generation.value_object.generation_counts import (
    GenerationCountsVO,
)
from src.modules.feed_builder.domain.generation.value_object.generation_definition_snapshot import (
    GenerationDefinitionSnapshotVO,
)
from src.modules.feed_builder.domain.generation.value_object.generation_failure import (
    GenerationFailureVO,
)
from src.modules.feed_builder.domain.generation.value_object.generation_sequence import (
    GenerationSequenceVO,
)
from src.modules.feed_builder.domain.validation import require_datetime, require_integer


@dataclass(frozen=True, slots=True)
class FeedGeneration:
    """Корневой агрегат одного запроса сборки со снимком определения без ревизий."""

    id: FeedGenerationIdVO
    feed_id: FeedIdVO
    request_sequence: GenerationSequenceVO
    definition_snapshot: GenerationDefinitionSnapshotVO
    status: GenerationStatus
    calculation_context: GenerationCalculationContextVO | None
    attempt_count: int
    current_attempt: GenerationAttemptVO | None
    counts: GenerationCountsVO
    failure: GenerationFailureVO | None
    artifact: FeedArtifact | None
    requested_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        identifier: FeedGenerationIdVO,
        feed_id: FeedIdVO,
        request_sequence: GenerationSequenceVO,
        definition_snapshot: GenerationDefinitionSnapshotVO,
        now: datetime,
    ) -> Self:
        """Создаёт PENDING-задание без попыток, расчётного контекста и результатов."""
        return cls.restore(
            identifier=identifier,
            feed_id=feed_id,
            request_sequence=request_sequence,
            definition_snapshot=definition_snapshot,
            status=GenerationStatus.PENDING,
            calculation_context=None,
            attempt_count=0,
            current_attempt=None,
            counts=GenerationCountsVO(),
            failure=None,
            artifact=None,
            requested_at=now,
            started_at=None,
            finished_at=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: FeedGenerationIdVO,
        feed_id: FeedIdVO,
        request_sequence: GenerationSequenceVO,
        definition_snapshot: GenerationDefinitionSnapshotVO,
        status: GenerationStatus,
        calculation_context: GenerationCalculationContextVO | None,
        attempt_count: int,
        current_attempt: GenerationAttemptVO | None,
        counts: GenerationCountsVO,
        failure: GenerationFailureVO | None,
        artifact: FeedArtifact | None,
        requested_at: datetime,
        started_at: datetime | None,
        finished_at: datetime | None,
    ) -> Self:
        """Проверяет снимок, состояние выполнения и единственный результат без активации."""
        if (
            not isinstance(identifier, FeedGenerationIdVO)
            or not isinstance(feed_id, FeedIdVO)
            or not isinstance(request_sequence, GenerationSequenceVO)
            or not isinstance(definition_snapshot, GenerationDefinitionSnapshotVO)
            or not isinstance(status, GenerationStatus)
            or not isinstance(counts, GenerationCountsVO)
            or (
                calculation_context is not None
                and not isinstance(calculation_context, GenerationCalculationContextVO)
            )
            or (
                current_attempt is not None
                and not isinstance(current_attempt, GenerationAttemptVO)
            )
            or (failure is not None and not isinstance(failure, GenerationFailureVO))
            or (artifact is not None and not isinstance(artifact, FeedArtifact))
        ):
            raise InvalidGenerationValueError(
                "Нужны типизированные свойства генерации."
            )
        require_integer(attempt_count, minimum=0, error=InvalidGenerationValueError)
        require_datetime(requested_at, error=InvalidGenerationValueError)
        for value in (started_at, finished_at):
            if value is not None:
                require_datetime(value, error=InvalidGenerationValueError)
                if value < requested_at:
                    raise InvalidGenerationValueError(
                        "Выполнение предшествует запросу."
                    )
        if (
            finished_at is not None
            and started_at is not None
            and finished_at < started_at
        ):
            raise InvalidGenerationValueError("Завершение предшествует началу.")
        if (attempt_count > 0) != (started_at is not None):
            raise InvalidGenerationValueError(
                "Начало выполнения не соответствует числу попыток."
            )
        if current_attempt is not None:
            if (
                current_attempt.number != attempt_count
                or started_at is None
                or current_attempt.claimed_at < started_at
            ):
                raise InvalidGenerationValueError(
                    "Текущая попытка не соответствует истории запуска."
                )
        if calculation_context is not None:
            if (
                started_at is None
                or calculation_context.as_of < started_at
                or (finished_at is not None and calculation_context.as_of > finished_at)
            ):
                raise InvalidGenerationValueError(
                    "Время расчёта вне интервала выполнения."
                )
        elif counts.exported_items or counts.rejected_items:
            raise InvalidGenerationValueError(
                "Обработка позиций требует зафиксированного расчётного контекста."
            )
        if status is GenerationStatus.PENDING:
            if (
                attempt_count != 0
                or calculation_context is not None
                or counts != GenerationCountsVO()
                or finished_at is not None
            ):
                raise InvalidGenerationValueError(
                    "PENDING не содержит выполненной работы."
                )
        if status is GenerationStatus.RUNNING:
            if current_attempt is None or finished_at is not None:
                raise InvalidGenerationValueError(
                    "RUNNING требует незавершённую попытку."
                )
        elif current_attempt is not None:
            raise InvalidGenerationValueError(
                "Текущая попытка допустима только в RUNNING."
            )
        if status in (GenerationStatus.SUCCEEDED, GenerationStatus.FAILED):
            if finished_at is None:
                raise InvalidGenerationValueError(
                    "Завершённое задание требует finished_at."
                )
        elif finished_at is not None:
            raise InvalidGenerationValueError(
                "Незавершённое задание не имеет finished_at."
            )
        if status is GenerationStatus.SUCCEEDED:
            if (
                artifact is None
                or calculation_context is None
                or counts.exported_items + counts.rejected_items != counts.total_items
                or counts.rejected_items != 0
            ):
                raise InvalidGenerationValueError(
                    "Успех STRICT требует контекст, полный учёт и файл без отклонённых позиций."
                )
        elif artifact is not None:
            raise InvalidGenerationValueError(
                "Итоговый файл допустим только для SUCCEEDED."
            )
        if (status is GenerationStatus.FAILED) != (failure is not None):
            raise InvalidGenerationValueError(
                "Причина ошибки обязательна только для FAILED."
            )
        if attempt_count == 0 and counts != GenerationCountsVO():
            raise InvalidGenerationValueError(
                "До первой попытки счётчики должны быть нулевыми."
            )
        if artifact is not None:
            artifact = FeedArtifact.restore(
                identifier=artifact.id,
                format=artifact.format,
                storage_key=artifact.storage_key,
                content_type=artifact.content_type,
                checksum=artifact.checksum,
                size_bytes=artifact.size_bytes,
                created_at=artifact.created_at,
            )
            if (
                artifact.format
                is not definition_snapshot.export_settings.format_settings.format
                or started_at is None
                or artifact.created_at < started_at
                or finished_at is None
                or artifact.created_at > finished_at
            ):
                raise InvalidGenerationValueError(
                    "Файл не соответствует формату или интервалу генерации."
                )
        definition_snapshot = GenerationDefinitionSnapshotVO(
            schema=FeedSchemaStructurePolicy.validate(definition_snapshot.schema),
            export_settings=definition_snapshot.export_settings,
            calculation_engine_version=definition_snapshot.calculation_engine_version,
        )
        return cls(
            id=identifier,
            feed_id=feed_id,
            request_sequence=request_sequence,
            definition_snapshot=definition_snapshot,
            status=status,
            calculation_context=calculation_context,
            attempt_count=attempt_count,
            current_attempt=current_attempt,
            counts=counts,
            failure=failure,
            artifact=artifact,
            requested_at=requested_at,
            started_at=started_at,
            finished_at=finished_at,
        )
