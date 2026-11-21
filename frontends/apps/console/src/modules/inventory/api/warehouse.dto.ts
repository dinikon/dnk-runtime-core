export interface CreateWarehouseRequestDTO {
  code: string;
  name: string;
}
export interface CreateWarehouseResponseDTO {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
  default_storage_location_id: string;
}
export interface GetWarehouseResponseDTO {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
  default_storage_location_id: string | null;
}
export interface PatchWarehouseRequestDTO {
  code?: string;
  name?: string;
  is_active?: boolean;
}
export interface PatchWarehouseResponseDTO {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
  default_storage_location_id: string | null;
}
export interface WarehouseListItemDTO {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
  default_storage_location_id: string | null;
}
export interface ListWarehousesResponseDTO {
  items: WarehouseListItemDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface ListWarehousesRequestDTO {
  search?: string;
  is_active?: boolean;
  offset: number;
  limit: number;
}
