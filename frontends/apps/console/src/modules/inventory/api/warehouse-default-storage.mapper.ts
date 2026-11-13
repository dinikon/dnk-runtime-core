import type { Warehouse } from "../model/warehouse.types.ts";
import type { WarehouseDefaultStorageValues } from "../model/warehouse-default-storage.types.ts";
import type {
  SetWarehouseDefaultStorageRequestDTO,
  SetWarehouseDefaultStorageResponseDTO,
} from "./warehouse-default-storage.dto.ts";
import { warehouseFromDto } from "./warehouse.mapper.ts";

export function warehouseDefaultStorageToDto(
  values: WarehouseDefaultStorageValues,
): SetWarehouseDefaultStorageRequestDTO {
  return { location_id: values.locationId };
}

export function warehouseDefaultStorageFromDto(
  dto: SetWarehouseDefaultStorageResponseDTO,
): Warehouse {
  return warehouseFromDto(dto);
}
