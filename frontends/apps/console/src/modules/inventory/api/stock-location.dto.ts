import type { StockLocationType } from "../model/stock-location.types.ts";
export interface CreateStockLocationRequestDTO {
  code: string;
  name: string;
  location_type: StockLocationType;
  parent_location_id: string | null;
}
export interface CreateStockLocationResponseDTO {
  id: string;
  warehouse_id: string;
  parent_location_id: string | null;
  code: string;
  name: string;
  location_type: StockLocationType;
  is_active: boolean;
}
export interface GetStockLocationResponseDTO {
  id: string;
  warehouse_id: string;
  parent_location_id: string | null;
  code: string;
  name: string;
  location_type: StockLocationType;
  is_active: boolean;
}
export interface PatchStockLocationResponseDTO {
  id: string;
  warehouse_id: string;
  parent_location_id: string | null;
  code: string;
  name: string;
  location_type: StockLocationType;
  is_active: boolean;
}
export interface StockLocationListItemDTO {
  id: string;
  warehouse_id: string;
  parent_location_id: string | null;
  code: string;
  name: string;
  location_type: StockLocationType;
  is_active: boolean;
}
export interface PatchStockLocationRequestDTO {
  code?: string;
  name?: string;
  is_active?: boolean;
}
export interface ListStockLocationsRequestDTO {
  offset: number;
  limit: number;
  search?: string;
  is_active?: boolean;
  location_type?: StockLocationType;
  parent_location_id?: string;
}
export interface ListStockLocationsResponseDTO {
  items: StockLocationListItemDTO[];
  total: number;
  offset: number;
  limit: number;
}
