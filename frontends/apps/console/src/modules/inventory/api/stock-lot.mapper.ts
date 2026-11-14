import type {
  GetStockLotResponseDTO,
  CreateStockLotRequestDTO,
  ListStockLotsResponseDTO,
} from "./stock-lot.dto.ts";
import type {
  StockLot,
  StockLotValues,
  StockLotsPage,
  StockLotsListParams,
} from "../model/stock-lot.types.ts";
export function stockLotFromDto(dto: GetStockLotResponseDTO): StockLot {
  return {
    id: dto.id,
    inventoryItemId: dto.inventory_item_id,
    number: dto.number,
    manufacturedOn: dto.manufactured_on,
    expiresOn: dto.expires_on,
  };
}
export function stockLotCreateToDto(
  values: StockLotValues,
): CreateStockLotRequestDTO {
  return {
    number: values.number,
    manufactured_on: values.manufacturedOn || null,
    expires_on: values.expiresOn || null,
  };
}
export function stockLotsPageFromDto(
  dto: ListStockLotsResponseDTO,
): StockLotsPage {
  return {
    items: dto.items.map(stockLotFromDto),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
  };
}
export function stockLotsParamsToDto(params: StockLotsListParams): {
  search?: string;
  offset: number;
  limit: number;
} {
  return {
    search: params.search.trim() || undefined,
    offset: params.offset,
    limit: params.limit,
  };
}
