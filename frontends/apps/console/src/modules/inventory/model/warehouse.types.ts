export interface Warehouse {
  id: string;
  code: string;
  name: string;
  isActive: boolean;
  defaultStorageLocationId: string | null;
}
export interface WarehouseCreateValues {
  code: string;
  name: string;
}
export interface WarehouseEditValues extends WarehouseCreateValues {
  isActive: boolean;
}
export type WarehouseChanges = Partial<WarehouseEditValues>;
export type WarehouseFieldErrors = Partial<
  Record<keyof WarehouseEditValues, string>
>;
export type WarehouseActivity = "all" | "active" | "inactive";
export interface WarehousesListParams {
  search: string;
  isActive: boolean | null;
  offset: number;
  limit: number;
}
export interface WarehousesPageParams {
  search: string;
  activity: WarehouseActivity;
  page: number;
  limit: number;
}
export interface WarehousesPage {
  items: Warehouse[];
  total: number;
  offset: number;
  limit: number;
}
