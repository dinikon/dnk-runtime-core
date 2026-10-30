export interface RepresentationFieldOriginDto {
  kind:
    | "catalog"
    | "catalog_parent"
    | "missing"
    | "group_override"
    | "item_override";
  catalog_position_id: string | null;
}
export interface RepresentationContentDto {
  locale: string;
  title: string | null;
  body: string | null;
  gallery: { file_id: string; alt: string; caption: string }[] | null;
  origins: {
    title: RepresentationFieldOriginDto;
    body: RepresentationFieldOriginDto;
    gallery: RepresentationFieldOriginDto;
  };
}
export interface RepresentationIssueDto {
  code: string;
  publication_id: string | null;
  field: string | null;
  locale: string | null;
}
export interface PreviewRepresentationResponseDto {
  state: RepresentationStateDto;
  export_blockers: string[];
  draft: boolean;
  representation: {
    channel_id: string;
    connection_id: string;
    binding_group_id: string;
    binding_revision: number;
    config_revision: number;
    platform: string;
    mode: "SIMPLE_TO_SIMPLE" | "VARIABLE_TO_SIMPLE" | "VARIABLE_TO_VARIABLE";
    locales: string[];
    as_of: string;
    binding_state: "linked" | "partial" | "conflict";
    issues: RepresentationIssueDto[];
    targets: {
      publication_id: string;
      external_id: string | null;
      parent_publication_id: string | null;
      publication_kind: string | null;
      binding_item_id: string | null;
      catalog_position_id: string;
      role: "container" | "position";
      content: RepresentationContentDto[];
      catalog_content: RepresentationContentDto[];
      ready: boolean;
      issues: RepresentationIssueDto[];
    }[];
  };
}

export interface LocalizedOverridesDto {
  title?: string | null;
  body?: string | null;
  gallery?: { file_id: string; alt: string; caption: string }[] | null;
}
export interface RepresentationOverridesDto {
  common: Record<string, LocalizedOverridesDto>;
  items: Record<string, Record<string, LocalizedOverridesDto>>;
}
export interface RepresentationStateDto {
  id: string | null;
  revision: number;
  export_enabled: boolean;
  overrides: RepresentationOverridesDto;
  created_at: string | null;
  updated_at: string | null;
  created_by: string | null;
  updated_by: string | null;
}
export interface RepresentationDetailsFieldsDto {
  state: RepresentationStateDto;
  binding_revision: number;
  config_revision: number;
  locales: string[];
  items: { id: string; catalog_position_id: string; publication_id: string }[];
}
export type GetRepresentationResponseDto = RepresentationDetailsFieldsDto;
export type SaveRepresentationResponseDto = RepresentationDetailsFieldsDto;
export type EnableRepresentationResponseDto = RepresentationDetailsFieldsDto;
export type DisableRepresentationResponseDto = RepresentationDetailsFieldsDto;
export interface RepresentationVersionDto {
  expected_revision: number;
  expected_binding_revision: number;
  expected_config_revision: number;
}
export interface SaveRepresentationRequestDto extends RepresentationVersionDto {
  overrides: RepresentationOverridesDto;
}
