export interface RepresentationFieldOriginDto {
  kind: "catalog" | "catalog_parent" | "missing";
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
      ready: boolean;
      issues: RepresentationIssueDto[];
    }[];
  };
}
