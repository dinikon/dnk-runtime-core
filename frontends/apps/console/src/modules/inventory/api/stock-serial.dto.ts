export interface CreateStockSerialResponseDTO {
  id: string;
  inventory_item_id: string;
  number: string;
  lot_id: string | null;
  lot_number: string | null;
  date_source: "NONE" | "LOT";
  manufactured_on: string | null;
  expires_on: string | null;
}
export interface GetStockSerialResponseDTO {
  id: string;
  inventory_item_id: string;
  number: string;
  lot_id: string | null;
  lot_number: string | null;
  date_source: "NONE" | "LOT";
  manufactured_on: string | null;
  expires_on: string | null;
}
export interface StockSerialListItemDTO {
  id: string;
  inventory_item_id: string;
  number: string;
  lot_id: string | null;
  lot_number: string | null;
  date_source: "NONE" | "LOT";
  manufactured_on: string | null;
  expires_on: string | null;
}
export interface CreateStockSerialRequestDTO {
  number: string;
  lot_id: string | null;
}
export interface ListStockSerialsResponseDTO {
  items: StockSerialListItemDTO[];
  total: number;
  offset: number;
  limit: number;
}
