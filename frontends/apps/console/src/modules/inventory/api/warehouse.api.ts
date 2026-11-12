import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  Warehouse,
  WarehouseCreateValues,
  WarehouseChanges,
  WarehouseFieldErrors,
  WarehousesListParams,
  WarehousesPage,
} from "../model/warehouse.types";
import { WarehouseRequestError } from "../model/warehouse.errors";
import type {
  CreateWarehouseResponseDTO,
  GetWarehouseResponseDTO,
  PatchWarehouseResponseDTO,
  ListWarehousesResponseDTO,
} from "./warehouse.dto";
import {
  warehouseFromDto,
  warehouseCreateToDto,
  warehousePatchToDto,
  warehousesPageFromDto,
  warehousesParamsToDto,
} from "./warehouse.mapper";

function requestError(cause: unknown, fallback: string): never {
  if (isCancel(cause)) throw cause;
  const status = getApiErrorStatus(cause),
    fields: WarehouseFieldErrors = {};
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
      if (field === "code" || field === "name")
        fields[field] = "Проверьте значение поля.";
      if (field === "is_active")
        fields.isActive = "Выберите активность склада.";
    }
  if (status === 409) fields.code = "Этот код склада уже занят.";
  throw new WarehouseRequestError(
    status === 403
      ? "Нет доступа к складам."
      : status === 404
        ? "Склад не найден."
        : getApiErrorMessage(cause, fallback),
    status,
    fields,
  );
}
export async function listWarehouses(
  params: WarehousesListParams,
  signal?: AbortSignal,
): Promise<WarehousesPage> {
  try {
    const { data } = await httpClient.get<ListWarehousesResponseDTO>(
      "/console/inventory/warehouses",
      { params: warehousesParamsToDto(params), signal },
    );
    return warehousesPageFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось загрузить склады.");
  }
}
export async function getWarehouse(
  id: string,
  signal?: AbortSignal,
): Promise<Warehouse> {
  try {
    const { data } = await httpClient.get<GetWarehouseResponseDTO>(
      `/console/inventory/warehouses/${encodeURIComponent(id)}`,
      { signal },
    );
    return warehouseFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось загрузить склад.");
  }
}
export async function createWarehouse(
  values: WarehouseCreateValues,
  signal?: AbortSignal,
): Promise<Warehouse> {
  try {
    const { data } = await httpClient.post<CreateWarehouseResponseDTO>(
      "/console/inventory/warehouses",
      warehouseCreateToDto(values),
      { signal },
    );
    return warehouseFromDto(data);
  } catch (error: unknown) {
    return requestError(error, "Не удалось создать склад.");
  }
}
export async function patchWarehouse(
  id: string,
  values: WarehouseChanges,
  signal?: AbortSignal,
): Promise<Warehouse> {
  try {
    const { data } = await httpClient.patch<PatchWarehouseResponseDTO>(
      `/console/inventory/warehouses/${encodeURIComponent(id)}`,
      warehousePatchToDto(values),
      { signal },
    );
    return warehouseFromDto(data);
  } catch (error: unknown) {
    return requestError(
      error,
      "Не удалось сохранить склад. Ваш ввод сохранён.",
    );
  }
}
