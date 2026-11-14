import type {
  GetStockSerialResponseDTO,
  CreateStockSerialRequestDTO,
  ListStockSerialsResponseDTO,
} from "./stock-serial.dto.ts";
import type {
  StockSerial,
  StockSerialValues,
  StockSerialsPage,
  StockSerialsListParams,
} from "../model/stock-serial.types.ts";
export function stockSerialFromDto(
  dto: GetStockSerialResponseDTO,
): StockSerial {
  return {
    id: dto.id,
    inventoryItemId: dto.inventory_item_id,
    number: dto.number,
    lotId: dto.lot_id,
    lotNumber: dto.lot_number,
    dateSource: dto.date_source,
    manufacturedOn: dto.manufactured_on,
    expiresOn: dto.expires_on,
  };
}
export function stockSerialCreateToDto(
  values: StockSerialValues,
): CreateStockSerialRequestDTO {
  return {
    number: values.number,
    lot_id: values.lotId || null,
  };
}
export function stockSerialsPageFromDto(
  dto: ListStockSerialsResponseDTO,
): StockSerialsPage {
  return {
    items: dto.items.map(stockSerialFromDto),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
  };
}
export function stockSerialsParamsToDto(params: StockSerialsListParams): {
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
