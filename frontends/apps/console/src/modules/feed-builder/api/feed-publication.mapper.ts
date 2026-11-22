import type {
  PublicationDTO,
  ListPublicationsDTO,
  AddedPublicationsDTO,
  AddPublicationsDTO,
  ChangedPublicationDTO,
  VariantSelectionDTO,
} from "./feed-publication.dto.ts";
import type {
  Publication,
  PublicationPage,
  AddedPublications,
  AddPublications,
  ChangedPublication,
  PublicationChoice,
} from "../model/feed-publication.types.ts";
export function mapPublication(d: PublicationDTO): Publication {
  return {
    id: d.id,
    feedId: d.feed_id,
    itemId: d.catalog_item_id,
    variantId: d.catalog_variant_id,
    status: d.status,
    version: d.version,
    title: d.title,
    parentTitle: d.parent_title,
    sku: d.sku,
    kind: d.kind,
    sourceAvailable: d.source_available,
    overridesCount: d.overrides_count,
    createdAt: d.created_at,
    updatedAt: d.updated_at,
  };
}
export function mapPublications(d: ListPublicationsDTO): PublicationPage {
  return {
    feedId: d.feed_id,
    feedVersion: d.feed_version,
    feedStatus: d.feed_status,
    items: d.items.map(mapPublication),
    total: d.total,
    counts: d.counts,
  };
}
export function addPublicationsPayload(v: AddPublications): AddPublicationsDTO {
  return {
    expected_feed_version: v.expectedFeedVersion,
    item_references: v.references.map((r) => ({
      catalog_item_id: r.itemId,
      catalog_variant_id: r.variantId,
    })),
  };
}
export function mapAddedPublications(
  d: AddedPublicationsDTO,
): AddedPublications {
  return {
    feedId: d.feed_id,
    feedVersion: d.feed_version,
    items: d.items.map((i) => ({
      id: i.id,
      itemId: i.catalog_item_id,
      variantId: i.catalog_variant_id,
      status: i.status,
      version: i.version,
      outcome: i.outcome,
    })),
  };
}
export function mapChangedPublication(
  d: ChangedPublicationDTO,
): ChangedPublication {
  return {
    id: d.id,
    version: d.version,
    status: d.status,
    updatedAt: d.updated_at,
  };
}
export function mapVariantSelection(
  d: VariantSelectionDTO,
): PublicationChoice[] {
  return d.items.map((i) => ({
    itemId: i.catalog_item_id,
    variantId: i.catalog_variant_id,
    title: i.title ?? i.sku ?? i.catalog_variant_id,
    sku: i.sku,
    kind: "variant",
  }));
}
