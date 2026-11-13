export type StockLocationType =
  "STORAGE" | "RECEIVING" | "SHIPPING" | "QUARANTINE" | "TRANSIT";
export interface StockLocation {
  id: string;
  warehouseId: string;
  parentLocationId: string | null;
  code: string;
  name: string;
  locationType: StockLocationType;
  isActive: boolean;
}
export interface StockLocationCreateValues {
  code: string;
  name: string;
  locationType: StockLocationType;
  parentLocationId: string | null;
}
export interface StockLocationCreateFormValues extends Omit<
  StockLocationCreateValues,
  "locationType"
> {
  locationType: StockLocationType | "";
}
export interface StockLocationEditValues {
  code: string;
  name: string;
  isActive: boolean;
}
export type StockLocationChanges = Partial<StockLocationEditValues>;
export type StockLocationFieldErrors = Partial<
  Record<
    keyof StockLocationCreateFormValues | keyof StockLocationEditValues,
    string
  >
>;
export type StockLocationActivity = "all" | "active" | "inactive";
export interface StockLocationsListParams {
  search: string;
  isActive: boolean | null;
  locationType: StockLocationType | null;
  parentLocationId: string | null;
  offset: number;
  limit: number;
}
export interface StockLocationsPageParams {
  search: string;
  activity: StockLocationActivity;
  locationType: StockLocationType | null;
  parentLocationId: string | null;
  page: number;
  limit: number;
}
export interface StockLocationsPage {
  items: StockLocation[];
  total: number;
  offset: number;
  limit: number;
}
