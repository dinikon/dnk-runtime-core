from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MockWorkplacesMetaDTO:
    contract_version: str
    generated_at: str


@dataclass(frozen=True, slots=True)
class MockWorkplacesUserDTO:
    id: str
    name: str
    email: str


@dataclass(frozen=True, slots=True)
class MockWorkplaceDTO:
    id: str
    emoji: str
    title: str
    description: str
    default_entity_key: str


@dataclass(frozen=True, slots=True)
class MockWorkplacesDataDTO:
    user: MockWorkplacesUserDTO
    workplaces: list[MockWorkplaceDTO] = field(default_factory=list)
    active_workplace_id: str = ""


@dataclass(frozen=True, slots=True)
class MockWorkplacesResultDTO:
    meta: MockWorkplacesMetaDTO
    data: MockWorkplacesDataDTO


@dataclass(frozen=True, slots=True)
class MockWorkplaceHeaderDTO:
    id: str
    emoji: str
    title: str


@dataclass(frozen=True, slots=True)
class MockWorkplaceEntityItemDTO:
    entity_key: str
    title: str
    emoji: str


@dataclass(frozen=True, slots=True)
class MockWorkplaceEntityGroupDTO:
    type: str
    items: list[MockWorkplaceEntityItemDTO] = field(default_factory=list)
    title: str | None = None
    emoji: str | None = None


@dataclass(frozen=True, slots=True)
class MockWorkplaceDetailsMetaDTO:
    workplace: MockWorkplaceHeaderDTO


@dataclass(frozen=True, slots=True)
class MockWorkplaceDetailsDataDTO:
    entity_groups: list[MockWorkplaceEntityGroupDTO] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class MockWorkplaceDetailsResultDTO:
    meta: MockWorkplaceDetailsMetaDTO
    data: MockWorkplaceDetailsDataDTO


@dataclass(frozen=True, slots=True)
class MockWorkplaceEntityDetailsMetaDTO:
    entity_key: str
    workplace_id: str


@dataclass(frozen=True, slots=True)
class MockWorkplaceEntityFeaturesDTO:
    custom_fields: bool
    pipelines: bool
    timeline: bool
    robots: bool


@dataclass(frozen=True, slots=True)
class MockWorkplaceEntityDetailsDTO:
    key: str
    title: str
    emoji: str
    features: MockWorkplaceEntityFeaturesDTO


@dataclass(frozen=True, slots=True)
class MockWorkplaceEntityViewDTO:
    id: str
    type: str
    title: str
    is_default: bool = False


@dataclass(frozen=True, slots=True)
class MockWorkplaceEntityPayloadDTO:
    entity: MockWorkplaceEntityDetailsDTO
    views: list[MockWorkplaceEntityViewDTO] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class MockWorkplaceEntityResultDTO:
    meta: MockWorkplaceEntityDetailsMetaDTO
    data: MockWorkplaceEntityPayloadDTO
