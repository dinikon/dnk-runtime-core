export interface SetWarehouseDefaultStorageRequestDTO {
  location_id: string;
}

export interface SetWarehouseDefaultStorageResponseDTO {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
  default_storage_location_id: string;
}
