import type {
  PublicationItemDto,
  PublicationCardDto,
  ListPublicationsDto,
  GetPublicationDto,
  SyncRunDto,
  StartSyncRunDto,
} from "./publication.dto";
import type {
  PublicationItem,
  PublicationCard,
  PublicationPage,
  PublicationDetails,
  PublicationSyncRun,
  StartedPublicationSync,
} from "../model/publication.types";

export function mapStartedSyncRun(
  dto: StartSyncRunDto,
): StartedPublicationSync {
  return { id: dto.id, status: dto.status };
}

export function mapPublicationItem(dto: PublicationItemDto): PublicationItem {
  return {
    id: dto.id,
    externalId: dto.external_id,
    kind: dto.kind,
    title: dto.title,
    sku: dto.sku,
    url: dto.url,
    mainImageUrl: dto.main_image_url,
    price: dto.price,
    regularPrice: dto.regular_price,
    salePrice: dto.sale_price,
    currency: dto.currency,
    quantity: dto.quantity,
    stockMode: dto.stock_mode,
    stockSourcePublicationId: dto.stock_source_publication_id,
    availability: dto.availability,
    status: dto.status,
    lastSeenAt: dto.last_seen_at,
    staleConfiguration: dto.stale_configuration,
  };
}
export function mapPublicationCard(dto: PublicationCardDto): PublicationCard {
  return {
    id: dto.id,
    rootKind: dto.root_kind,
    bindings: (dto.bindings ?? []).map((v) => ({
      id: v.id,
      catalogRootId: v.catalog_root_id,
      catalogTitle: v.catalog_title,
      mode: v.mode,
      state: v.state,
    })),
    rootExternalId: dto.root_external_id,
    rootSku: dto.root_sku,
    rootMainImageUrl: dto.root_main_image_url,
    title: dto.title,
    selectedPublicationId: dto.selected_publication_id,
    items: dto.items.map(mapPublicationItem),
    minPrice: dto.min_price,
    maxPrice: dto.max_price,
    currency: dto.currency,
    lastSeenAt: dto.last_seen_at,
  };
}
export function mapPublicationPage(dto: ListPublicationsDto): PublicationPage {
  return {
    items: dto.items.map(mapPublicationCard),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
    locale: dto.locale,
    locales: dto.locales,
  };
}
export function mapPublicationDetails(
  dto: GetPublicationDto,
): PublicationDetails {
  return {
    card: mapPublicationCard(dto.card),
    locale: dto.locale,
    locales: dto.locales,
  };
}
export function mapSyncRun(dto: SyncRunDto): PublicationSyncRun {
  return {
    id: dto.id,
    configRevision: dto.config_revision,
    revision: dto.revision,
    status: dto.status,
    processedCount: dto.processed_count,
    skippedCount: dto.skipped_count,
    pagesCount: dto.pages_count,
    automatic: dto.automatic,
    errorCode: dto.error_code,
    createdAt: dto.created_at,
    startedAt: dto.started_at,
    finishedAt: dto.finished_at,
    recoveryRequired: dto.recovery_required,
  };
}
