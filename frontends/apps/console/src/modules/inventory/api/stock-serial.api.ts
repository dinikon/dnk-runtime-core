import type { StockSerialChanges } from "../model/stock-serial.types";
import type { PatchStockSerialResponseDTO } from "./stock-serial.dto";
import { stockSerialPatchToDto } from "./stock-serial.mapper";
import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import { StockSerialRequestError } from "../model/stock-serial.errors";
import type {
  StockSerial,
  StockSerialErrors,
  StockSerialValues,
  StockSerialsListParams,
  StockSerialsPage,
} from "../model/stock-serial.types";
import type {
  CreateStockSerialResponseDTO,
  GetStockSerialResponseDTO,
  ListStockSerialsResponseDTO,
} from "./stock-serial.dto";
import {
  stockSerialFromDto,
  stockSerialCreateToDto,
  stockSerialsPageFromDto,
  stockSerialsParamsToDto,
} from "./stock-serial.mapper";
function requestError(cause: unknown, fallback: string): never {
  if (isCancel(cause)) throw cause;
  const status = getApiErrorStatus(cause),
    fields: StockSerialErrors = {};
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
      if (field === "number") fields.number = "Проверьте номер экземпляра.";
      if (field === "lot_id") fields.lotId = "Проверьте выбранную партию.";
    }
  if (status === 409)
    fields.number = "Номер экземпляра уже занят внутри этого SKU.";
  throw new StockSerialRequestError(
    status === 403
      ? "Нет доступа к серийным экземплярам SKU."
      : status === 404
        ? "SKU, экземпляр или выбранная партия не найдены."
        : getApiErrorMessage(cause, fallback),
    status,
    fields,
  );
}
function base(itemId: string): string {
  return `/console/inventory/items/${encodeURIComponent(itemId)}/serials`;
}
export async function listStockSerials(
  itemId: string,
  params: StockSerialsListParams,
  signal?: AbortSignal,
): Promise<StockSerialsPage> {
  try {
    const { data } = await httpClient.get<ListStockSerialsResponseDTO>(
      base(itemId),
      { params: stockSerialsParamsToDto(params), signal },
    );
    return stockSerialsPageFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось загрузить экземпляра.");
  }
}
export async function getStockSerial(
  itemId: string,
  serialId: string,
  signal?: AbortSignal,
): Promise<StockSerial> {
  try {
    const { data } = await httpClient.get<GetStockSerialResponseDTO>(
      `${base(itemId)}/${encodeURIComponent(serialId)}`,
      { signal },
    );
    return stockSerialFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось загрузить экземпляр.");
  }
}
export async function createStockSerial(
  itemId: string,
  values: StockSerialValues,
  signal?: AbortSignal,
): Promise<StockSerial> {
  try {
    const { data } = await httpClient.post<CreateStockSerialResponseDTO>(
      base(itemId),
      stockSerialCreateToDto(values),
      { signal },
    );
    return stockSerialFromDto(data);
  } catch (error: unknown) {
    return requestError(
      error,
      "Не удалось создать экземпляр. Ваш ввод сохранён.",
    );
  }
}

export async function patchStockSerial(
  itemId: string,
  serialId: string,
  changes: StockSerialChanges,
  signal?: AbortSignal,
): Promise<StockSerial> {
  try {
    const { data } = await httpClient.patch<PatchStockSerialResponseDTO>(
      `${base(itemId)}/${encodeURIComponent(serialId)}`,
      stockSerialPatchToDto(changes),
      { signal },
    );
    return stockSerialFromDto(data);
  } catch (error: unknown) {
    return requestError(
      error,
      "Не удалось подтвердить сохранение экземпляра. Ваш ввод сохранён.",
    );
  }
}
