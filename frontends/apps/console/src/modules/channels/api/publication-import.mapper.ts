import type { GetPublicationImportResponseDto } from "./publication-import.dto";
import type { PublicationImport } from "../model/publication-import.types";
import { mapDraftValues } from "./catalog-links.mapper";
export function mapPublicationImport(
  dto: GetPublicationImportResponseDto,
): PublicationImport {
  return {
    id: dto.preparation_id,
    publicationId: dto.publication_id,
    status: dto.status,
    revision: dto.revision,
    observedRevision: dto.observed_revision,
    expiresAt: dto.expires_at,
    readAt: dto.read_at,
    errorCode: dto.error_code,
    values: dto.values
      ? {
          ...mapDraftValues(dto.values),
          copyPrices: dto.values.regular_price !== null,
          descriptions: { ...dto.values.descriptions },
          gallery: [...dto.values.gallery],
          primaryImageId: dto.values.primary_image_id,
        }
      : null,
    translations: Object.fromEntries(
      Object.entries(dto.translations).map(([code, value]) => [
        code,
        { ...value },
      ]),
    ),
    images: dto.images.map((image) => ({
      id: image.id,
      previewUrl: image.preview_url,
      alt: image.alt,
      errorCode: image.error_code,
    })),
    warnings: [...dto.warnings],
  };
}
