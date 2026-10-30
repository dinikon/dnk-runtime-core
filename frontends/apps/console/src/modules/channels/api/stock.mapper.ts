import type {
  BindingStockDto,
  RefreshPublicationStockRequestDto,
  ExportCatalogStockRequestDto,
} from "./stock.dto";
import type { BindingStock, StockRequest } from "../model/stock.types";
export function mapBindingStock(value: BindingStockDto): BindingStock {
  return {
    allowStockExport: value.allow_stock_export,
    warnings: [...value.warnings],
    items: value.items.map((v) => ({
      publicationId: v.publication_id,
      ownerId: v.stock_owner_id,
      catalogPositionId: v.catalog_position_id,
      catalogOwnerId: v.catalog_owner_id,
      catalogQuantity: v.catalog_quantity,
      publicationQuantity: v.publication_quantity,
      publicationAvailability: v.publication_availability,
      exportBlocker: v.export_blocker,
      desiredState: { ...v.desired_state },
      operation: v.operation
        ? {
            id: v.operation.operation_id,
            direction: v.operation.direction,
            status: v.operation.status,
            observedAt: v.operation.observed_at,
            desiredState: v.operation.desired_state
              ? { ...v.operation.desired_state }
              : null,
            errorCode: v.operation.error_code,
            recoveryRequired: v.operation.recovery_required,
          }
        : null,
    })),
  };
}
export function refreshStockPayload(
  value: StockRequest,
): RefreshPublicationStockRequestDto {
  return { publication_ids: [...value.publicationIds] };
}
export function exportStockPayload(): ExportCatalogStockRequestDto {
  return {};
}
