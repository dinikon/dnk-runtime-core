export interface CreateStockLotResponseDTO {
  id: string;
  inventory_item_id: string;
  number: string;
  manufactured_on: string | null;
  expires_on: string | null;
}
export interface GetStockLotResponseDTO {
  id: string;
  inventory_item_id: string;
  number: string;
  manufactured_on: string | null;
  expires_on: string | null;
}
export interface StockLotListItemDTO {
  id: string;
  inventory_item_id: string;
  number: string;
  manufactured_on: string | null;
  expires_on: string | null;
}

export interface CreateStockLotRequestDTO {
  number: string;
  manufactured_on: string | null;
  expires_on: string | null;
}
export interface ListStockLotsResponseDTO {
  items: StockLotListItemDTO[];
  total: number;
  offset: number;
  limit: number;
}

export interface PatchStockLotRequestDTO {
  manufactured_on?: string | null;
  expires_on?: string | null;
}
export interface PatchStockLotResponseDTO {
  id: string;
  inventory_item_id: string;
  number: string;
  manufactured_on: string | null;
  expires_on: string | null;
}
