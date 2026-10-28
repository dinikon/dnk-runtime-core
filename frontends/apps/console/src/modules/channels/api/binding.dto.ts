export interface BindingPairDto {
  catalog_position_id: string;
  publication_id: string;
}
export interface BindingPositionDto {
  id: string;
  kind: string;
  title: string | null;
  sku: string | null;
  image_url: string | null;
  status: string | null;
  price: string | null;
  currency: string | null;
  quantity: string | null;
  availability: string | null;
  stock_source_id: string;
  external_id: string | null;
  stale: boolean;
}
export interface BindingPreviewDto {
  catalog: {
    structure: { id: string; kind: string; positions: string[] };
    root: BindingPositionDto;
    positions: BindingPositionDto[];
  } | null;
  publications: BindingPositionDto[];
  assessment: {
    state: "linked" | "partial" | "conflict";
    issues: string[];
    catalog_count: number;
    publication_count: number;
    matched_count: number;
  };
  catalog_token: string;
  publication_token: string;
  suggestions: BindingPairDto[];
}
export interface BindingDto {
  group: {
    id: string;
    connection_id: string;
    channel_id: string;
    channel_name: string;
    platform: string;
    catalog_root_id: string;
    mode: "SIMPLE_TO_SIMPLE" | "VARIABLE_TO_VARIABLE" | "VARIABLE_TO_SIMPLE";
    publication_root_id: string | null;
    revision: number;
    items: BindingPairDto[];
    created_at: string;
    updated_at: string;
  };
  preview: BindingPreviewDto;
}
export interface BindingPageDto {
  items: BindingDto[];
  total: number;
  offset: number;
  limit: number;
}
export interface BindingCandidatesDto {
  items: BindingPositionDto[];
  occupied_ids: string[];
  total: number;
  offset: number;
  limit: number;
}
export interface BindingProposalDto {
  catalog_root_id: string;
  mode: "SIMPLE_TO_SIMPLE" | "VARIABLE_TO_VARIABLE" | "VARIABLE_TO_SIMPLE";
  publication_root_id: string | null;
  items: BindingPairDto[];
  locale: string;
  group_id?: string;
}
