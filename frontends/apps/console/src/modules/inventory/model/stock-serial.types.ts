export interface StockSerial {
  id: string;
  inventoryItemId: string;
  number: string;
  lotId: string | null;
  lotNumber: string | null;
  dateSource: "NONE" | "LOT";
  manufacturedOn: string | null;
  expiresOn: string | null;
}
export interface StockSerialValues {
  number: string;
  lotId: string;
}
export type StockSerialErrors = Partial<
  Record<keyof StockSerialValues, string>
>;
export interface StockSerialsListParams {
  search: string;
  offset: number;
  limit: number;
}
export interface StockSerialsPageParams {
  search: string;
  page: number;
  limit: number;
}
export interface StockSerialsPage {
  items: StockSerial[];
  total: number;
  offset: number;
  limit: number;
}
