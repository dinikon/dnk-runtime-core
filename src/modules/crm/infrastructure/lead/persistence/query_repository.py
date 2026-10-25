from src.modules.crm.infrastructure.persistence.models.contact import ContactModel
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel
from uuid import UUID
from collections.abc import Mapping
from typing import Any
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.application.lead.port.read_row import LeadReadRowDTO
from src.modules.crm.infrastructure.persistence.models.lead import LeadModel


class SqlAlchemyLeadQueryRepository:
    """SQL-проекции своих карточек без восстановления Domain."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию tenant UoW."""
        self._session = session

    async def _rows(self, rows: list[Mapping[str, Any]]) -> tuple[LeadReadRowDTO, ...]:
        """Собирает собственную проекцию обращения без восстановления агрегата."""
        return tuple(
            LeadReadRowDTO(
                **{
                    k: row[k]
                    for k in [
                        "id",
                        "title",
                        "created_at",
                        "updated_at",
                        "created_by",
                        "updated_by",
                        "first_name",
                        "last_name",
                        "middle_name",
                        "company_name",
                        "contact_id",
                        "company_id",
                        "conversion_result",
                        "funnel_id",
                        "stage_id",
                        "position_revision",
                    ]
                }
            )
            for row in rows
        )

    async def get(self, record_id: UUID) -> LeadReadRowDTO | None:
        """Читает одну проекцию."""
        row = (
            (
                await self._session.execute(
                    select(LeadModel.__table__).where(LeadModel.id == record_id)
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
    ) -> tuple[tuple[LeadReadRowDTO, ...], int]:
        """Применяет серверные фильтры, пагинацию и устойчивую сортировку."""
        conditions = []
        if funnel_id:
            conditions.append(LeadModel.funnel_id == funnel_id)
        if stage_id:
            conditions.append(LeadModel.stage_id == stage_id)
        if search:
            term = (
                "%"
                + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                + "%"
            )
            conditions.append(
                or_(
                    LeadModel.title.ilike(term, escape="\\"),
                    LeadModel.first_name.ilike(term, escape="\\"),
                    LeadModel.last_name.ilike(term, escape="\\"),
                    LeadModel.company_name.ilike(term, escape="\\"),
                    func.concat_ws(
                        " ",
                        LeadModel.first_name,
                        LeadModel.last_name,
                        LeadModel.middle_name,
                    ).ilike(term, escape="\\"),
                    func.concat_ws(
                        " ",
                        LeadModel.last_name,
                        LeadModel.first_name,
                        LeadModel.middle_name,
                    ).ilike(term, escape="\\"),
                    select(ContactModel.id)
                    .where(
                        ContactModel.id == LeadModel.contact_id,
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
                    .exists(),
                    select(CompanyModel.id)
                    .where(
                        CompanyModel.id == LeadModel.company_id,
                        CompanyModel.legal_name.ilike(term, escape="\\"),
                    )
                    .exists(),
                )
            )
        if converted is not None:
            conditions.append(
                LeadModel.conversion_result.is_not(None)
                if converted
                else LeadModel.conversion_result.is_(None)
            )
        total = (
            await self._session.execute(
                select(func.count()).select_from(LeadModel).where(*conditions)
            )
        ).scalar_one()
        order = (
            LeadModel.title.asc() if sort == "title" else LeadModel.updated_at.desc()
        )
        rows = (
            (
                await self._session.execute(
                    select(LeadModel.__table__)
                    .where(*conditions)
                    .order_by(order, LeadModel.id)
                    .offset(offset)
                    .limit(limit)
                )
            )
            .mappings()
            .all()
        )
        return await self._rows(list(rows)), total
