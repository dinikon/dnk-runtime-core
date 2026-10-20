import type * as DTO from "./catalog-links.dto";
import type * as Model from "../model/catalog-links.types";
export function mapCandidate(
  dto: DTO.CatalogCandidateDto,
): Model.CatalogCandidate {
  return {
    id: dto.id,
    title: dto.title,
    sku: dto.sku,
    status: dto.status,
    canBind: dto.can_bind,
    reasonCode: dto.reason_code,
    representationRevision: dto.representation_revision,
  };
}
export function mapDraftValues(
  dto: DTO.PreviewCatalogDraftValuesDto,
): Model.DraftValues {
  return {
    titles: { ...dto.titles },
    sku: dto.sku,
    regularPrice: dto.regular_price,
    salePrice: dto.sale_price,
    currency: dto.currency,
    manageStock: dto.manage_stock,
    quantity: dto.quantity,
    stockStatus: dto.stock_status,
    backorders: dto.backorders,
  };
}
export function mapPreview(
  dto: DTO.PreviewCatalogDraftResponseDto,
  publicationId: string,
  locale: string,
): Model.DraftPreview {
  return {
    publicationId,
    locale,
    observedRevision: dto.observed_revision,
    values: mapDraftValues(dto.values),
    issues: dto.issues.map((i) => ({ ...i })),
    warnings: dto.warnings,
    mainImageUrl: dto.main_image_url,
    origins: { ...dto.origins },
  };
}
export function createDraftPayload(
  input: Model.CreateDraftInput,
): DTO.CreateCatalogDraftRequestDto {
  const v = input.values;
  return {
    ...(input.preparationId
      ? {
          preparation_id: input.preparationId,
          expected_preparation_revision: input.preparationRevision,
        }
      : {}),
    request_key: input.requestKey,
    expected_observed_revision: input.observedRevision,
    values: {
      titles: { ...v.titles },
      ...(v.descriptions ? { descriptions: { ...v.descriptions } } : {}),
      ...(v.gallery
        ? {
            gallery: [...v.gallery],
            primary_image_id: v.primaryImageId ?? null,
          }
        : {}),
      sku: v.sku,
      regular_price: v.regularPrice,
      sale_price: v.salePrice,
      currency: v.currency,
      manage_stock: v.manageStock,
      quantity: v.quantity,
      stock_status: v.stockStatus,
      backorders: v.backorders,
    },
  };
}
export function mapCreatedDraft(
  dto: DTO.CreateCatalogDraftResponseDto,
): Model.CreatedCatalogDraft {
  return {
    catalogItemId: dto.catalog_item_id,
    representationId: dto.representation_id,
    bindingId: dto.binding_id,
  };
}
export function mapBound(
  dto: DTO.BindPublicationResponseDto,
): Model.BoundPublication {
  return { ...mapCreatedDraft(dto), revision: dto.revision };
}
