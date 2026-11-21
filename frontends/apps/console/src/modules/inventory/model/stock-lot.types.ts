export interface StockLot {
  id: string;
  inventoryItemId: string;
  number: string;
  manufacturedOn: string | null;
  expiresOn: string | null;
}
export interface StockLotDatesValues {
  manufacturedOn: string;
  expiresOn: string;
}
export interface StockLotValues extends StockLotDatesValues {
  number: string;
}
export type StockLotDatesChanges = Partial<StockLotDatesValues>;
export type StockLotDatesErrors = Partial<
  Record<keyof StockLotDatesValues, string>
>;
export type StockLotErrors = Partial<Record<keyof StockLotValues, string>>;
export interface StockLotsListParams {
  search: string;
  offset: number;
  limit: number;
}
export interface StockLotsPageParams {
  search: string;
  page: number;
  limit: number;
}
export interface StockLotsPage {
  items: StockLot[];
  total: number;
  offset: number;
  limit: number;
}
