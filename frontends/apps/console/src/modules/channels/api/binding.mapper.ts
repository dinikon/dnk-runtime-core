import type {
  BindingDto,
  BindingPositionDto,
  BindingPreviewDto,
  BindingProposalDto,
} from "./binding.dto";
import type {
  CatalogBinding,
  BindingPosition,
  BindingPreview,
  BindingProposal,
} from "../model/bindings/binding.types";
export function bindingPosition(v: BindingPositionDto): BindingPosition {
  return {
    id: v.id,
    kind: v.kind,
    title: v.title,
    sku: v.sku,
    imageUrl: v.image_url,
    status: v.status,
    price: v.price,
    currency: v.currency,
    quantity: v.quantity,
    availability: v.availability,
    stockSourceId: v.stock_source_id,
    externalId: v.external_id,
    stale: v.stale,
  };
}
export function bindingPreview(v: BindingPreviewDto): BindingPreview {
  return {
    catalogRoot: v.catalog ? bindingPosition(v.catalog.root) : null,
    catalogPositions: v.catalog?.positions.map(bindingPosition) ?? [],
    publications: v.publications.map(bindingPosition),
    state: v.assessment.state,
    issues: [...v.assessment.issues],
    catalogCount: v.assessment.catalog_count,
    publicationCount: v.assessment.publication_count,
    matchedCount: v.assessment.matched_count,
    catalogToken: v.catalog_token,
    publicationToken: v.publication_token,
    suggestions: v.suggestions.map((p) => ({
      catalogId: p.catalog_position_id,
      publicationId: p.publication_id,
    })),
  };
}
export function catalogBinding(v: BindingDto): CatalogBinding {
  return {
    id: v.group.id,
    channelId: v.group.channel_id,
    channelName: v.group.channel_name,
    platform: v.group.platform,
    catalogRootId: v.group.catalog_root_id,
    mode: v.group.mode,
    publicationRootId: v.group.publication_root_id,
    revision: v.group.revision,
    items: v.group.items.map((p) => ({
      catalogId: p.catalog_position_id,
      publicationId: p.publication_id,
    })),
    preview: bindingPreview(v.preview),
    updatedAt: v.group.updated_at,
  };
}
export function bindingProposal(v: BindingProposal): BindingProposalDto {
  return {
    catalog_root_id: v.catalogRootId,
    mode: v.mode,
    publication_root_id: v.publicationRootId,
    items: v.items.map((p) => ({
      catalog_position_id: p.catalogId,
      publication_id: p.publicationId,
    })),
    locale: v.locale,
    ...(v.groupId ? { group_id: v.groupId } : {}),
  };
}
