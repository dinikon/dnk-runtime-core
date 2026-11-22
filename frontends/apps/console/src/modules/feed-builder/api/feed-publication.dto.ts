export interface PublicationDTO {
  id: string;
  feed_id: string;
  catalog_item_id: string;
  catalog_variant_id: string | null;
  status: "DRAFT" | "ENABLED" | "PAUSED" | "ARCHIVED";
  version: number;
  title: string | null;
  parent_title: string | null;
  sku: string | null;
  kind: string | null;
  source_available: boolean;
  overrides_count: number;
  created_at: string;
  updated_at: string;
}
export interface ListPublicationsDTO {
  feed_id: string;
  feed_version: number;
  feed_status: string;
  items: PublicationDTO[];
  total: number;
  counts: Partial<Record<PublicationDTO["status"], number>>;
}
export interface GetPublicationDTO {
  publication: PublicationDTO;
  feed_version: number;
  feed_status: string;
}
export interface AddPublicationsDTO {
  expected_feed_version: number;
  item_references: {
    catalog_item_id: string;
    catalog_variant_id: string | null;
  }[];
}
export interface AddedPublicationsDTO {
  feed_id: string;
  feed_version: number;
  items: {
    id: string;
    catalog_item_id: string;
    catalog_variant_id: string | null;
    status: PublicationDTO["status"];
    version: number;
    outcome: "CREATED" | "EXISTING";
  }[];
}
export interface ChangedPublicationDTO {
  id: string;
  status: PublicationDTO["status"];
  version: number;
  updated_at: string;
}
export interface VariantSelectionDTO {
  items: {
    catalog_item_id: string;
    catalog_variant_id: string;
    title: string | null;
    sku: string | null;
  }[];
}
