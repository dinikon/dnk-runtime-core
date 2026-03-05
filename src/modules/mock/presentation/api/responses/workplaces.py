from pydantic import BaseModel, Field


class MockWorkplacesMetaResponseSchema(BaseModel):
    contractVersion: str
    generatedAt: str


class MockWorkplacesUserResponseSchema(BaseModel):
    id: str
    name: str
    email: str


class MockWorkplaceSummaryResponseSchema(BaseModel):
    id: str
    emoji: str
    title: str
    description: str
    defaultEntityKey: str


class MockWorkplacesDataResponseSchema(BaseModel):
    user: MockWorkplacesUserResponseSchema
    workplaces: list[MockWorkplaceSummaryResponseSchema] = Field(
        default_factory=list
    )
    activeWorkplaceId: str


class MockWorkplacesResponseSchema(BaseModel):
    meta: MockWorkplacesMetaResponseSchema
    data: MockWorkplacesDataResponseSchema


class MockWorkplaceHeaderResponseSchema(BaseModel):
    id: str
    emoji: str
    title: str


class MockWorkplaceEntityItemResponseSchema(BaseModel):
    entityKey: str
    title: str
    emoji: str


class MockWorkplaceEntityGroupResponseSchema(BaseModel):
    type: str
    title: str | None = None
    emoji: str | None = None
    items: list[MockWorkplaceEntityItemResponseSchema] = Field(default_factory=list)


class MockWorkplaceDetailsMetaResponseSchema(BaseModel):
    workplace: MockWorkplaceHeaderResponseSchema


class MockWorkplaceDetailsDataResponseSchema(BaseModel):
    entityGroups: list[MockWorkplaceEntityGroupResponseSchema] = Field(
        default_factory=list
    )


class MockWorkplaceDetailsResponseSchema(BaseModel):
    meta: MockWorkplaceDetailsMetaResponseSchema
    data: MockWorkplaceDetailsDataResponseSchema


class MockWorkplaceEntityMetaResponseSchema(BaseModel):
    entityKey: str
    workplaceId: str


class MockWorkplaceEntityFeaturesResponseSchema(BaseModel):
    customFields: bool
    pipelines: bool
    timeline: bool
    robots: bool


class MockWorkplaceEntityDetailsResponseSchema(BaseModel):
    key: str
    title: str
    emoji: str
    features: MockWorkplaceEntityFeaturesResponseSchema


class MockWorkplaceEntityViewResponseSchema(BaseModel):
    id: str
    type: str
    title: str
    isDefault: bool | None = None


class MockWorkplaceEntityDataResponseSchema(BaseModel):
    entity: MockWorkplaceEntityDetailsResponseSchema
    views: list[MockWorkplaceEntityViewResponseSchema] = Field(default_factory=list)


class MockWorkplaceEntityResponseSchema(BaseModel):
    meta: MockWorkplaceEntityMetaResponseSchema
    data: MockWorkplaceEntityDataResponseSchema
