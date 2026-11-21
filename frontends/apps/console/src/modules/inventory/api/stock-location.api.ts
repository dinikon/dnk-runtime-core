import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  StockLocation,
  StockLocationCreateValues,
  StockLocationChanges,
  StockLocationFieldErrors,
  StockLocationsListParams,
  StockLocationsPage,
} from "../model/stock-location.types";
import { StockLocationRequestError } from "../model/stock-location.errors";
import type {
  CreateStockLocationResponseDTO,
  GetStockLocationResponseDTO,
  PatchStockLocationResponseDTO,
  ListStockLocationsResponseDTO,
} from "./stock-location.dto";
import {
  stockLocationFromDto,
  stockLocationsPageFromDto,
  stockLocationCreateToDto,
  stockLocationPatchToDto,
  stockLocationsParamsToDto,
} from "./stock-location.mapper";
function requestError(cause: unknown, fallback: string): never {
  if (isCancel(cause)) throw cause;
  const status = getApiErrorStatus(cause),
    fields: StockLocationFieldErrors = {};
  const detail: unknown = isAxiosError(cause)
    ? cause.response?.data?.detail
    : undefined;
  if (status === 422 && Array.isArray(detail))
    for (const issue of detail) {
      if (
        typeof issue !== "object" ||
        issue === null ||
        !Array.isArray(issue.loc)
      )
        continue;
      const field: unknown = issue.loc[1];
      if (field === "code" || field === "name")
        fields[field] = "Проверьте значение поля.";
      if (field === "is_active")
        fields.isActive = "Проверьте активность локации.";
      if (field === "location_type")
        fields.locationType = "Выберите тип локации.";
      if (field === "parent_location_id")
        fields.parentLocationId = "Выберите родительскую локацию.";
    }
  throw new StockLocationRequestError(
    status === 403
      ? "Нет доступа к локациям склада."
      : status === 404
        ? "Склад или локация не найдены."
        : getApiErrorMessage(cause, fallback),
    status,
    fields,
  );
}
function locationsPath(warehouseId: string): string {
  return `/console/inventory/warehouses/${encodeURIComponent(warehouseId)}/locations`;
}
export async function listStockLocations(
  warehouseId: string,
  params: StockLocationsListParams,
  signal?: AbortSignal,
): Promise<StockLocationsPage> {
  try {
    const { data } = await httpClient.get<ListStockLocationsResponseDTO>(
      locationsPath(warehouseId),
      { params: stockLocationsParamsToDto(params), signal },
    );
    return stockLocationsPageFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось загрузить локации.");
  }
}
export async function getStockLocation(
  warehouseId: string,
  id: string,
  signal?: AbortSignal,
): Promise<StockLocation> {
  try {
    const { data } = await httpClient.get<GetStockLocationResponseDTO>(
      `${locationsPath(warehouseId)}/${encodeURIComponent(id)}`,
      { signal },
    );
    return stockLocationFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось загрузить локацию.");
  }
}
export async function createStockLocation(
  warehouseId: string,
  values: StockLocationCreateValues,
  signal?: AbortSignal,
): Promise<StockLocation> {
  try {
    const { data } = await httpClient.post<CreateStockLocationResponseDTO>(
      locationsPath(warehouseId),
      stockLocationCreateToDto(values),
      { signal },
    );
    return stockLocationFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось создать локацию.");
  }
}
export async function patchStockLocation(
  warehouseId: string,
  id: string,
  values: StockLocationChanges,
  signal?: AbortSignal,
): Promise<StockLocation> {
  try {
    const { data } = await httpClient.patch<PatchStockLocationResponseDTO>(
      `${locationsPath(warehouseId)}/${encodeURIComponent(id)}`,
      stockLocationPatchToDto(values),
      { signal },
    );
    return stockLocationFromDto(data);
  } catch (error: unknown) {
    return requestError(
      error,
      "Не удалось сохранить локацию. Ваш ввод сохранён.",
    );
  }
}
