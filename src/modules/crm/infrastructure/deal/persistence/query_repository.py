from src.modules.crm.infrastructure.persistence.models.contact import ContactModel
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel
from uuid import UUID
from collections.abc import Mapping
from typing import Any
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.application.deal.port.read_row import DealReadRowDTO
from src.modules.crm.infrastructure.persistence.models.deal import DealModel
from src.modules.crm.infrastructure.persistence.models.deal_contact import (
    DealContactModel,
)
from src.modules.crm.infrastructure.persistence.models.deal_company import (
    DealCompanyModel,
)


class SqlAlchemyDealQueryRepository:
    """SQL-проекции своих карточек без восстановления Domain."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию tenant UoW."""
        self._session = session

    async def _rows(self, rows: list[Mapping[str, Any]]) -> tuple[DealReadRowDTO, ...]:
        """Собирает проекции, пакетно получая участников страницы."""
        related = {}
        ids = [row["id"] for row in rows]
        for model, field, key in (
            (DealContactModel, DealContactModel.contact_id, "contact_ids"),
            (DealCompanyModel, DealCompanyModel.company_id, "company_ids"),
        ):
            values = (
                (
                    await self._session.execute(
                        select(model.deal_id, field)
                        .where(model.deal_id.in_(ids))
                        .order_by(field)
                    )
                ).all()
                if ids
                else []
            )
            for record_id, participant_id in values:
                related.setdefault(record_id, {}).setdefault(key, []).append(
                    participant_id
                )
        return tuple(
            DealReadRowDTO(
                **{
                    k: row[k]
                    for k in [
                        "id",
                        "title",
                        "created_at",
                        "updated_at",
                        "created_by",
                        "updated_by",
                        "source_lead_id",
                        "source_lead_snapshot",
                        "lifecycle_state",
                        "funnel_id",
                        "stage_id",
                        "position_revision",
                    ]
                },
                contact_ids=tuple(related.get(row["id"], {}).get("contact_ids", [])),
                company_ids=tuple(related.get(row["id"], {}).get("company_ids", [])),
            )
            for row in rows
        )

    async def get(self, record_id: UUID) -> DealReadRowDTO | None:
        """Читает одну проекцию."""
        row = (
            (
                await self._session.execute(
                    select(DealModel.__table__).where(DealModel.id == record_id)
                )
            )
            .mappings()
            .one_or_none()
        )
        return (await self._rows([row]))[0] if row else None

    async def list(
        self,
        *,
        funnel_id: UUID | None,
        stage_id: UUID | None,
        search: str,
        converted: bool | None,
        offset: int,
        limit: int,
        sort: str,
    ) -> tuple[tuple[DealReadRowDTO, ...], int]:
        """Применяет серверные фильтры, пагинацию и устойчивую сортировку."""
        conditions = []
        if funnel_id:
            conditions.append(DealModel.funnel_id == funnel_id)
        if stage_id:
            conditions.append(DealModel.stage_id == stage_id)
        if search:
            term = (
                "%"
                + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                + "%"
            )
            contact_match = (
                select(DealContactModel.contact_id)
                .join(ContactModel, ContactModel.id == DealContactModel.contact_id)
                .where(
                    DealContactModel.deal_id == DealModel.id,
                    or_(
                        func.concat_ws(
                            " ",
                            ContactModel.first_name,
                            ContactModel.last_name,
                            ContactModel.middle_name,
                        ).ilike(term, escape="\\"),
                        func.concat_ws(
                            " ",
                            ContactModel.last_name,
                            ContactModel.first_name,
                            ContactModel.middle_name,
                        ).ilike(term, escape="\\"),
                    ),
                )
                .exists()
            )
            company_match = (
                select(DealCompanyModel.company_id)
                .join(CompanyModel, CompanyModel.id == DealCompanyModel.company_id)
                .where(
                    DealCompanyModel.deal_id == DealModel.id,
                    CompanyModel.legal_name.ilike(term, escape="\\"),
                )
                .exists()
            )
            source = DealModel.source_lead_snapshot
            conditions.append(
                or_(
                    DealModel.title.ilike(term, escape="\\"),
                    contact_match,
                    company_match,
                    func.concat_ws(
                        " ",
                        source["first_name"].as_string(),
                        source["last_name"].as_string(),
                        source["company_name"].as_string(),
                    ).ilike(term, escape="\\"),
                    func.concat_ws(
                        " ",
                        source["last_name"].as_string(),
                        source["first_name"].as_string(),
                    ).ilike(term, escape="\\"),
                )
            )

        total = (
            await self._session.execute(
                select(func.count()).select_from(DealModel).where(*conditions)
            )
        ).scalar_one()
        order = (
            DealModel.title.asc() if sort == "title" else DealModel.updated_at.desc()
        )
        rows = (
            (
                await self._session.execute(
                    select(DealModel.__table__)
                    .where(*conditions)
                    .order_by(order, DealModel.id)
                    .offset(offset)
                    .limit(limit)
                )
            )
            .mappings()
            .all()
        )
        return await self._rows(list(rows)), total
