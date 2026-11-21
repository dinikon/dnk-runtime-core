import type {
  Warehouse,
  WarehouseCreateValues,
  WarehouseChanges,
  WarehousesListParams,
  WarehousesPage,
} from "../model/warehouse.types.ts";
import type {
  CreateWarehouseRequestDTO,
  CreateWarehouseResponseDTO,
  GetWarehouseResponseDTO,
  PatchWarehouseRequestDTO,
  PatchWarehouseResponseDTO,
  WarehouseListItemDTO,
  ListWarehousesRequestDTO,
  ListWarehousesResponseDTO,
} from "./warehouse.dto.ts";

export function warehouseFromDto(
  dto:
    | CreateWarehouseResponseDTO
    | GetWarehouseResponseDTO
    | PatchWarehouseResponseDTO
    | WarehouseListItemDTO,
): Warehouse {
  return {
    id: dto.id,
    code: dto.code,
    name: dto.name,
    isActive: dto.is_active,
    defaultStorageLocationId: dto.default_storage_location_id,
  };
}
export function warehousesPageFromDto(
  dto: ListWarehousesResponseDTO,
): WarehousesPage {
  return {
    items: dto.items.map(warehouseFromDto),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
  };
}
export function warehouseCreateToDto(
  values: WarehouseCreateValues,
): CreateWarehouseRequestDTO {
  return { code: values.code, name: values.name };
}
export function warehousePatchToDto(
  values: WarehouseChanges,
): PatchWarehouseRequestDTO {
  const dto: PatchWarehouseRequestDTO = {};
  if (values.code !== undefined) dto.code = values.code;
  if (values.name !== undefined) dto.name = values.name;
  if (values.isActive !== undefined) dto.is_active = values.isActive;
  return dto;
}
export function warehousesParamsToDto(
  params: WarehousesListParams,
): ListWarehousesRequestDTO {
  return {
    offset: params.offset,
    limit: params.limit,
    ...(params.search ? { search: params.search } : {}),
    ...(params.isActive !== null ? { is_active: params.isActive } : {}),
  };
}
