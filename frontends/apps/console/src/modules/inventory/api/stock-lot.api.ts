import type { PatchStockLotResponseDTO } from "./stock-lot.dto";
import { stockLotDatesPatchToDto } from "./stock-lot.mapper";
import type { StockLotDatesChanges } from "../model/stock-lot.types";
import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import { StockLotRequestError } from "../model/stock-lot.errors";
import type {
  StockLot,
  StockLotErrors,
  StockLotValues,
  StockLotsListParams,
  StockLotsPage,
} from "../model/stock-lot.types";
import type {
  CreateStockLotResponseDTO,
  GetStockLotResponseDTO,
  ListStockLotsResponseDTO,
} from "./stock-lot.dto";
import {
  stockLotFromDto,
  stockLotCreateToDto,
  stockLotsPageFromDto,
  stockLotsParamsToDto,
} from "./stock-lot.mapper";
function requestError(cause: unknown, fallback: string): never {
  if (isCancel(cause)) throw cause;
  const status = getApiErrorStatus(cause),
    fields: StockLotErrors = {};
  const detail: unknown = isAxiosError(cause)
    ? cause.response?.data?.detail
    : undefined;
  if (Array.isArray(detail))
    for (const issue of detail) {
      if (
        typeof issue !== "object" ||
        issue === null ||
        !Array.isArray(issue.loc)
      )
        continue;
      const field: unknown = issue.loc[1];
      if (field === "number") fields.number = "Проверьте номер партии.";
      if (field === "manufactured_on")
        fields.manufacturedOn = "Проверьте дату производства.";
      if (field === "expires_on") fields.expiresOn = "Проверьте срок годности.";
    }
  if (status === 409)
    fields.number = "Номер партии уже занят внутри этого SKU.";
  throw new StockLotRequestError(
    status === 403
      ? "Нет доступа к партиям SKU."
      : status === 404
        ? "SKU или партия не найдены."
        : getApiErrorMessage(cause, fallback),
    status,
    fields,
  );
}
function base(itemId: string): string {
  return `/console/inventory/items/${encodeURIComponent(itemId)}/lots`;
}
export async function listStockLots(
  itemId: string,
  params: StockLotsListParams,
  signal?: AbortSignal,
): Promise<StockLotsPage> {
  try {
    const { data } = await httpClient.get<ListStockLotsResponseDTO>(
      base(itemId),
      { params: stockLotsParamsToDto(params), signal },
    );
    return stockLotsPageFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось загрузить партии.");
  }
}
export async function getStockLot(
  itemId: string,
  lotId: string,
  signal?: AbortSignal,
): Promise<StockLot> {
  try {
    const { data } = await httpClient.get<GetStockLotResponseDTO>(
      `${base(itemId)}/${encodeURIComponent(lotId)}`,
      { signal },
    );
    return stockLotFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось загрузить партию.");
  }
}
export async function createStockLot(
  itemId: string,
  values: StockLotValues,
  signal?: AbortSignal,
): Promise<StockLot> {
  try {
    const { data } = await httpClient.post<CreateStockLotResponseDTO>(
      base(itemId),
      stockLotCreateToDto(values),
      { signal },
    );
    return stockLotFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось создать партию. Ваш ввод сохранён.");
  }
}

export async function patchStockLotDates(
  itemId: string,
  lotId: string,
  changes: StockLotDatesChanges,
  signal?: AbortSignal,
): Promise<StockLot> {
  try {
    const { data } = await httpClient.patch<PatchStockLotResponseDTO>(
      `${base(itemId)}/${encodeURIComponent(lotId)}`,
      stockLotDatesPatchToDto(changes),
      { signal },
    );
    return stockLotFromDto(data);
  } catch (error: unknown) {
    return requestError(
      error,
      "Не удалось сохранить даты партии. Ваш ввод сохранён.",
    );
  }
}
