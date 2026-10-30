from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from src.modules.channels.application.content_feed.import_contracts import (
    FeedImportDetails,
)


class FeedImportIssueFields(BaseModel):
    """Очищенная ошибка этапа без текста и ссылок внешнего провайдера."""

    code: str
    stage: str


class FeedImportReportFields(BaseModel):
    """Отчёт провайдера не заменяет проверку каждого поля."""

    status: str
    total: int | None
    updated: int | None
    created: int | None
    imported: int | None
    not_changed: int | None
    not_in_file: int | None
    with_errors_count: int | None
    issues: list[FeedImportIssueFields]


class FeedFieldVerificationFields(BaseModel):
    """Публичное доказательство состояния поля выбранной локали."""

    field: str
    locale: str | None
    status: str


class FeedPublicationVerificationFields(BaseModel):
    """Наблюдаемые результаты одной цели с безопасными URL CDN."""

    publication_id: UUID
    external_id: str
    import_key: str
    fields: list[FeedFieldVerificationFields]
    observed_gallery: list[str]


class FeedImportFields(BaseModel):
    """Публичная проекция; секретный запрос и credentials исключены явно."""

    revision: int
    phase: str
    operation_id: UUID | None
    external_import_id: str | None
    submission: str
    force_update: bool
    requested_at: datetime | None
    submission_started_at: datetime | None
    last_checked_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    manual_resolution: str | None
    report: FeedImportReportFields | None
    verification: list[FeedPublicationVerificationFields]
    recovery_required: bool
    can_start: bool
    can_resume: bool
    can_attach: bool
    can_resolve: bool

    @classmethod
    def from_details(cls, value: FeedImportDetails) -> "FeedImportFields":
        """Разделяет принятие, отчёт и результат проверки без универсального dump Domain."""
        state = value.state
        report = state.report
        submission = (
            "accepted"
            if state.external_import_id is not None
            else (
                "unknown"
                if state.phase == "unknown"
                or state.phase == "needs_attention"
                and state.submission_started_at is not None
                else (
                    state.phase.value
                    if state.phase in {"queued", "submitting"}
                    else (
                        "rejected"
                        if state.error_code == "feed_import_rejected"
                        else "not_sent"
                    )
                )
            )
        )
        return cls(
            revision=state.revision,
            phase=state.phase.value,
            operation_id=state.operation_id.uuid if state.operation_id else None,
            external_import_id=state.external_import_id,
            submission=submission,
            force_update=state.force_update,
            requested_at=state.requested_at,
            submission_started_at=state.submission_started_at,
            last_checked_at=state.last_checked_at,
            finished_at=state.finished_at,
            error_code=state.error_code,
            manual_resolution=state.manual_resolution,
            report=(
                FeedImportReportFields(
                    status=report.status,
                    total=report.total,
                    updated=report.updated,
                    created=report.created,
                    imported=report.imported,
                    not_changed=report.not_changed,
                    not_in_file=report.not_in_file,
                    with_errors_count=report.with_errors_count,
                    issues=[
                        FeedImportIssueFields(code=v.code, stage=v.stage)
                        for v in report.issues
                    ],
                )
                if report
                else None
            ),
            verification=[
                FeedPublicationVerificationFields(
                    publication_id=v.publication_id.uuid,
                    external_id=v.external_id,
                    import_key=v.import_key,
                    fields=[
                        FeedFieldVerificationFields(
                            field=f.field, locale=f.locale, status=f.status
                        )
                        for f in v.fields
                    ],
                    observed_gallery=list(v.observed_gallery),
                )
                for v in state.verification
            ],
            recovery_required=value.recovery_required,
            can_start=value.can_start,
            can_resume=value.can_resume,
            can_attach=value.can_attach,
            can_resolve=value.can_resolve,
        )
