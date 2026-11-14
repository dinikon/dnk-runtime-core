from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.application.counterparty_reference.dto import (
    CounterpartyModelKey,
    CounterpartyReferenceDTO,
)
from src.modules.crm.application.counterparty_reference.query.search_counterparty_references.query import (
    SearchCounterpartyReferencesQuery,
)
from src.modules.crm.application.counterparty_reference.query.search_counterparty_references.dto import (
    SearchCounterpartyReferencesResultDTO,
)
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel
from src.modules.crm.infrastructure.counterparty_reference.query_mapper import (
    CounterpartyReferenceQueryMapper,
)


class SqlAlchemyCounterpartyReferenceRepository:
    """Читает оба вида контрагентов на сессии внешнего tenant-UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию без владения транзакцией."""
        self._session = session

    async def get(
        self, model_key: CounterpartyModelKey, record_id: UUID, *, lock: bool = False
    ) -> CounterpartyReferenceDTO | None:
        """FOR KEY SHARE сериализует проверку выбранной записи с её удалением."""
        if model_key is CounterpartyModelKey.COMPANY:
            statement = (
                select(CompanyModel)
                .where(CompanyModel.id == record_id)
                .execution_options(populate_existing=True)
            )
            if lock:
                statement = statement.with_for_update(read=True, key_share=True)
            company = (await self._session.scalars(statement)).one_or_none()
            return (
                CounterpartyReferenceQueryMapper.company(company)
                if company is not None
                else None
            )
        statement_contact = (
            select(ContactModel)
            .where(ContactModel.id == record_id)
            .execution_options(populate_existing=True)
        )
        if lock:
            statement_contact = statement_contact.with_for_update(
                read=True, key_share=True
            )
        contact = (await self._session.scalars(statement_contact)).one_or_none()
        return (
            CounterpartyReferenceQueryMapper.contact(contact)
            if contact is not None
            else None
        )

    async def get_many(
        self, references: tuple[tuple[CounterpartyModelKey, UUID], ...]
    ) -> dict[tuple[CounterpartyModelKey, UUID], CounterpartyReferenceDTO]:
        """Делает не более одного запроса на тип, не смешивая одинаковые UUID."""
        result: dict[tuple[CounterpartyModelKey, UUID], CounterpartyReferenceDTO] = {}
        companies = tuple(
            identifier
            for key, identifier in references
            if key is CounterpartyModelKey.COMPANY
        )
        contacts = tuple(
            identifier
            for key, identifier in references
            if key is CounterpartyModelKey.CONTACT
        )
        if companies:
            statement = (
                select(CompanyModel)
                .where(CompanyModel.id.in_(companies))
                .execution_options(populate_existing=True)
            )
            for company in (await self._session.scalars(statement)).all():
                result[(CounterpartyModelKey.COMPANY, company.id)] = (
                    CounterpartyReferenceQueryMapper.company(company)
                )
        if contacts:
            statement_contacts = (
                select(ContactModel)
                .where(ContactModel.id.in_(contacts))
                .execution_options(populate_existing=True)
            )
            for contact in (await self._session.scalars(statement_contacts)).all():
                result[(CounterpartyModelKey.CONTACT, contact.id)] = (
                    CounterpartyReferenceQueryMapper.contact(contact)
                )
        return result

    async def search(
        self, query: SearchCounterpartyReferencesQuery
    ) -> SearchCounterpartyReferencesResultDTO:
        """Применяет одинаковый буквальный поиск к total и стабильной странице."""
        if query.model_key is CounterpartyModelKey.COMPANY:
            filters: tuple[ColumnElement[bool], ...] = (
                ()
                if query.search is None
                else (CompanyModel.legal_name.icontains(query.search, autoescape=True),)
            )
            total = (
                await self._session.execute(
                    select(func.count()).select_from(CompanyModel).where(*filters)
                )
            ).scalar_one()
            statement = (
                select(CompanyModel)
                .where(*filters)
                .order_by(CompanyModel.legal_name, CompanyModel.id)
                .offset(query.offset)
                .limit(query.limit)
                .execution_options(populate_existing=True)
            )
            items = tuple(
                CounterpartyReferenceQueryMapper.company(model)
                for model in (await self._session.scalars(statement)).all()
            )
        else:
            display_name: ColumnElement[str] = func.concat_ws(
                " ",
                ContactModel.last_name,
                ContactModel.first_name,
                ContactModel.middle_name,
            )
            contact_filters: tuple[ColumnElement[bool], ...] = (
                ()
                if query.search is None
                else (display_name.icontains(query.search, autoescape=True),)
            )
            total = (
                await self._session.execute(
                    select(func.count())
                    .select_from(ContactModel)
                    .where(*contact_filters)
                )
            ).scalar_one()
            statement_contact = (
                select(ContactModel)
                .where(*contact_filters)
                .order_by(
                    ContactModel.last_name.nulls_first(),
                    ContactModel.first_name,
                    ContactModel.middle_name.nulls_first(),
                    ContactModel.id,
                )
                .offset(query.offset)
                .limit(query.limit)
                .execution_options(populate_existing=True)
            )
            items = tuple(
                CounterpartyReferenceQueryMapper.contact(model)
                for model in (await self._session.scalars(statement_contact)).all()
            )
        return SearchCounterpartyReferencesResultDTO(
            items, total, query.offset, query.limit
        )
