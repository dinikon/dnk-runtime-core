from fastapi import APIRouter, HTTPException, status

from src.modules.mock.domain import MockCrmEntityNotFoundError
from src.modules.mock.presentation.api.responses.workplaces import (
    MockWorkplaceDetailsDataResponseSchema,
    MockWorkplaceDetailsMetaResponseSchema,
    MockWorkplaceDetailsResponseSchema,
    MockWorkplaceEntityDataResponseSchema,
    MockWorkplaceEntityDetailsResponseSchema,
    MockWorkplaceEntityGroupResponseSchema,
    MockWorkplaceEntityFeaturesResponseSchema,
    MockWorkplaceEntityItemResponseSchema,
    MockWorkplaceEntityMetaResponseSchema,
    MockWorkplaceEntityResponseSchema,
    MockWorkplaceEntityViewResponseSchema,
    MockWorkplaceHeaderResponseSchema,
    MockWorkplacesDataResponseSchema,
    MockWorkplacesMetaResponseSchema,
    MockWorkplacesResponseSchema,
    MockWorkplacesUserResponseSchema,
    MockWorkplaceSummaryResponseSchema,
)
from src.modules.mock.presentation.depends.use_cases import (
    MockCrmEntityUseCaseDep,
    MockCrmWorkplaceUseCaseDep,
    MockWorkplacesUseCaseDep,
)

router = APIRouter(tags=["mock"])


@router.get(
    "/api/mock/workplaces",
    response_model=MockWorkplacesResponseSchema,
)
async def get_mock_workplaces(
    use_case: MockWorkplacesUseCaseDep,
) -> MockWorkplacesResponseSchema:
    result = await use_case.execute()
    return MockWorkplacesResponseSchema(
        meta=MockWorkplacesMetaResponseSchema(
            contractVersion=result.meta.contract_version,
            generatedAt=result.meta.generated_at,
        ),
        data=MockWorkplacesDataResponseSchema(
            user=MockWorkplacesUserResponseSchema(
                id=result.data.user.id,
                name=result.data.user.name,
                email=result.data.user.email,
            ),
            workplaces=[
                MockWorkplaceSummaryResponseSchema(
                    id=workplace.id,
                    emoji=workplace.emoji,
                    title=workplace.title,
                    description=workplace.description,
                    defaultEntityKey=workplace.default_entity_key,
                )
                for workplace in result.data.workplaces
            ],
            activeWorkplaceId=result.data.active_workplace_id,
        ),
    )


@router.get(
    "/api/mock/workplaces/crm",
    response_model=MockWorkplaceDetailsResponseSchema,
    response_model_exclude_none=True,
)
async def get_mock_crm_workplace(
    use_case: MockCrmWorkplaceUseCaseDep,
) -> MockWorkplaceDetailsResponseSchema:
    result = await use_case.execute()
    return MockWorkplaceDetailsResponseSchema(
        meta=MockWorkplaceDetailsMetaResponseSchema(
            workplace=MockWorkplaceHeaderResponseSchema(
                id=result.meta.workplace.id,
                emoji=result.meta.workplace.emoji,
                title=result.meta.workplace.title,
            )
        ),
        data=MockWorkplaceDetailsDataResponseSchema(
            entityGroups=[
                MockWorkplaceEntityGroupResponseSchema(
                    type=group.type,
                    title=group.title,
                    emoji=group.emoji,
                    items=[
                        MockWorkplaceEntityItemResponseSchema(
                            entityKey=item.entity_key,
                            title=item.title,
                            emoji=item.emoji,
                        )
                        for item in group.items
                    ],
                )
                for group in result.data.entity_groups
            ]
        ),
    )


@router.get(
    "/api/mock/workplaces/crm/entities/{entity_key}",
    response_model=MockWorkplaceEntityResponseSchema,
    response_model_exclude_none=True,
)
async def get_mock_crm_entity(
    entity_key: str,
    use_case: MockCrmEntityUseCaseDep,
) -> MockWorkplaceEntityResponseSchema:
    try:
        result = await use_case.execute(entity_key=entity_key)
    except MockCrmEntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return MockWorkplaceEntityResponseSchema(
        meta=MockWorkplaceEntityMetaResponseSchema(
            entityKey=result.meta.entity_key,
            workplaceId=result.meta.workplace_id,
        ),
        data=MockWorkplaceEntityDataResponseSchema(
            entity=MockWorkplaceEntityDetailsResponseSchema(
                key=result.data.entity.key,
                title=result.data.entity.title,
                emoji=result.data.entity.emoji,
                features=MockWorkplaceEntityFeaturesResponseSchema(
                    customFields=result.data.entity.features.custom_fields,
                    pipelines=result.data.entity.features.pipelines,
                    timeline=result.data.entity.features.timeline,
                    robots=result.data.entity.features.robots,
                ),
            ),
            views=[
                MockWorkplaceEntityViewResponseSchema(
                    id=view.id,
                    type=view.type,
                    title=view.title,
                    isDefault=view.is_default if view.is_default else None,
                )
                for view in result.data.views
            ],
        ),
    )
