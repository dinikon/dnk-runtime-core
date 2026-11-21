import type {
  StockLocation,
  StockLocationCreateValues,
  StockLocationChanges,
  StockLocationsListParams,
  StockLocationsPage,
} from "../model/stock-location.types.ts";
import type {
  CreateStockLocationRequestDTO,
  CreateStockLocationResponseDTO,
  GetStockLocationResponseDTO,
  PatchStockLocationResponseDTO,
  StockLocationListItemDTO,
  PatchStockLocationRequestDTO,
  ListStockLocationsRequestDTO,
  ListStockLocationsResponseDTO,
} from "./stock-location.dto.ts";
export function stockLocationFromDto(
  dto:
    | CreateStockLocationResponseDTO
    | GetStockLocationResponseDTO
    | PatchStockLocationResponseDTO
    | StockLocationListItemDTO,
): StockLocation {
  return {
    id: dto.id,
    warehouseId: dto.warehouse_id,
    parentLocationId: dto.parent_location_id,
    code: dto.code,
    name: dto.name,
    locationType: dto.location_type,
    isActive: dto.is_active,
  };
}
export function stockLocationsPageFromDto(
  dto: ListStockLocationsResponseDTO,
): StockLocationsPage {
  return {
    items: dto.items.map(stockLocationFromDto),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
  };
}
export function stockLocationCreateToDto(
  value: StockLocationCreateValues,
): CreateStockLocationRequestDTO {
  return {
    code: value.code,
    name: value.name,
    location_type: value.locationType,
    parent_location_id: value.parentLocationId,
  };
}
export function stockLocationPatchToDto(
  value: StockLocationChanges,
): PatchStockLocationRequestDTO {
  const dto: PatchStockLocationRequestDTO = {};
  if (value.code !== undefined) dto.code = value.code;
  if (value.name !== undefined) dto.name = value.name;
  if (value.isActive !== undefined) dto.is_active = value.isActive;
  return dto;
}
export function stockLocationsParamsToDto(
  value: StockLocationsListParams,
): ListStockLocationsRequestDTO {
  return {
    offset: value.offset,
    limit: value.limit,
    ...(value.search ? { search: value.search } : {}),
    ...(value.isActive !== null ? { is_active: value.isActive } : {}),
    ...(value.locationType !== null
      ? { location_type: value.locationType }
      : {}),
    ...(value.parentLocationId !== null
      ? { parent_location_id: value.parentLocationId }
      : {}),
  };
}
