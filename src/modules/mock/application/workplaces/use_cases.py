from src.modules.mock.application.workplaces.dto import (
    MockWorkplaceDTO,
    MockWorkplaceDetailsDataDTO,
    MockWorkplaceDetailsMetaDTO,
    MockWorkplaceDetailsResultDTO,
    MockWorkplaceEntityDetailsDTO,
    MockWorkplaceEntityDetailsMetaDTO,
    MockWorkplaceEntityGroupDTO,
    MockWorkplaceEntityFeaturesDTO,
    MockWorkplaceEntityItemDTO,
    MockWorkplaceEntityPayloadDTO,
    MockWorkplaceEntityResultDTO,
    MockWorkplaceEntityViewDTO,
    MockWorkplaceHeaderDTO,
    MockWorkplacesDataDTO,
    MockWorkplacesMetaDTO,
    MockWorkplacesResultDTO,
    MockWorkplacesUserDTO,
)
from src.modules.mock.domain import MockCrmEntityNotFoundError


class GetMockWorkplacesUseCase:
    async def execute(self) -> MockWorkplacesResultDTO:
        return MockWorkplacesResultDTO(
            meta=MockWorkplacesMetaDTO(
                contract_version="1.0",
                generated_at="2026-03-05T20:00:00Z",
            ),
            data=MockWorkplacesDataDTO(
                user=MockWorkplacesUserDTO(
                    id="u_001",
                    name="Denis",
                    email="denis@example.com",
                ),
                workplaces=[
                    MockWorkplaceDTO(
                        id="crm",
                        emoji="🧩",
                        title="CRM",
                        description="Лиды, сделки, клиенты",
                        default_entity_key="deal",
                    ),
                    MockWorkplaceDTO(
                        id="support",
                        emoji="🎧",
                        title="Support",
                        description="Тикеты и обращения",
                        default_entity_key="ticket",
                    ),
                ],
                active_workplace_id="crm",
            ),
        )


class GetMockCrmWorkplaceUseCase:
    async def execute(self) -> MockWorkplaceDetailsResultDTO:
        return MockWorkplaceDetailsResultDTO(
            meta=MockWorkplaceDetailsMetaDTO(
                workplace=MockWorkplaceHeaderDTO(
                    id="crm",
                    emoji="🧩",
                    title="CRM",
                )
            ),
            data=MockWorkplaceDetailsDataDTO(
                entity_groups=[
                    MockWorkplaceEntityGroupDTO(
                        type="flat",
                        items=[
                            MockWorkplaceEntityItemDTO(
                                entity_key="lead",
                                title="Lead",
                                emoji="📥",
                            ),
                            MockWorkplaceEntityItemDTO(
                                entity_key="deal",
                                title="Deal",
                                emoji="💼",
                            ),
                        ],
                    ),
                    MockWorkplaceEntityGroupDTO(
                        type="dropdown",
                        title="Клиенты",
                        emoji="👥",
                        items=[
                            MockWorkplaceEntityItemDTO(
                                entity_key="contact",
                                title="Contact",
                                emoji="👤",
                            ),
                            MockWorkplaceEntityItemDTO(
                                entity_key="company",
                                title="Company",
                                emoji="🏢",
                            ),
                        ],
                    ),
                ]
            ),
        )


class GetMockCrmEntityUseCase:
    async def execute(self, entity_key: str) -> MockWorkplaceEntityResultDTO:
        entity = self._get_entity(entity_key)
        return MockWorkplaceEntityResultDTO(
            meta=MockWorkplaceEntityDetailsMetaDTO(
                entity_key=entity_key,
                workplace_id="crm",
            ),
            data=entity,
        )

    def _get_entity(self, entity_key: str) -> MockWorkplaceEntityPayloadDTO:
        entities: dict[str, MockWorkplaceEntityPayloadDTO] = {
            "deal": MockWorkplaceEntityPayloadDTO(
                entity=MockWorkplaceEntityDetailsDTO(
                    key="deal",
                    title="Deal",
                    emoji="💼",
                    features=MockWorkplaceEntityFeaturesDTO(
                        custom_fields=True,
                        pipelines=True,
                        timeline=True,
                        robots=True,
                    ),
                ),
                views=[
                    MockWorkplaceEntityViewDTO(
                        id="table_default",
                        type="table",
                        title="Таблица",
                        is_default=True,
                    ),
                    MockWorkplaceEntityViewDTO(
                        id="kanban_by_stage",
                        type="kanban",
                        title="Канбан (по стадиям)",
                    ),
                    MockWorkplaceEntityViewDTO(
                        id="calendar_by_close",
                        type="calendar",
                        title="Календарь (по закрытию)",
                    ),
                ],
            ),
            "lead": MockWorkplaceEntityPayloadDTO(
                entity=MockWorkplaceEntityDetailsDTO(
                    key="lead",
                    title="Lead",
                    emoji="📥",
                    features=MockWorkplaceEntityFeaturesDTO(
                        custom_fields=True,
                        pipelines=True,
                        timeline=True,
                        robots=False,
                    ),
                ),
                views=[
                    MockWorkplaceEntityViewDTO(
                        id="table_default",
                        type="table",
                        title="Таблица",
                        is_default=True,
                    ),
                    MockWorkplaceEntityViewDTO(
                        id="kanban_by_status",
                        type="kanban",
                        title="Канбан (по статусам)",
                    ),
                ],
            ),
            "contact": MockWorkplaceEntityPayloadDTO(
                entity=MockWorkplaceEntityDetailsDTO(
                    key="contact",
                    title="Contact",
                    emoji="👤",
                    features=MockWorkplaceEntityFeaturesDTO(
                        custom_fields=True,
                        pipelines=False,
                        timeline=True,
                        robots=False,
                    ),
                ),
                views=[
                    MockWorkplaceEntityViewDTO(
                        id="table_default",
                        type="table",
                        title="Таблица",
                        is_default=True,
                    ),
                    MockWorkplaceEntityViewDTO(
                        id="cards_by_segment",
                        type="board",
                        title="Карточки (по сегменту)",
                    ),
                ],
            ),
            "company": MockWorkplaceEntityPayloadDTO(
                entity=MockWorkplaceEntityDetailsDTO(
                    key="company",
                    title="Company",
                    emoji="🏢",
                    features=MockWorkplaceEntityFeaturesDTO(
                        custom_fields=True,
                        pipelines=False,
                        timeline=True,
                        robots=False,
                    ),
                ),
                views=[
                    MockWorkplaceEntityViewDTO(
                        id="table_default",
                        type="table",
                        title="Таблица",
                        is_default=True,
                    ),
                    MockWorkplaceEntityViewDTO(
                        id="map_by_address",
                        type="map",
                        title="Карта (по адресу)",
                    ),
                ],
            ),
        }
        result = entities.get(entity_key)
        if result is None:
            raise MockCrmEntityNotFoundError(entity_key)
        return result
