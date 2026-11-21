import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type { Warehouse } from "../model/warehouse.types";
import type {
  WarehouseDefaultStorageValues,
  WarehouseDefaultStorageFieldErrors,
} from "../model/warehouse-default-storage.types";
import { WarehouseDefaultStorageRequestError } from "../model/warehouse-default-storage.errors";
import type { SetWarehouseDefaultStorageResponseDTO } from "./warehouse-default-storage.dto";
import {
  warehouseDefaultStorageToDto,
  warehouseDefaultStorageFromDto,
} from "./warehouse-default-storage.mapper";

export async function setWarehouseDefaultStorage(
  warehouseId: string,
  values: WarehouseDefaultStorageValues,
  signal?: AbortSignal,
): Promise<Warehouse> {
  try {
    const { data } =
      await httpClient.put<SetWarehouseDefaultStorageResponseDTO>(
        `/console/inventory/warehouses/${encodeURIComponent(warehouseId)}/default-storage-location`,
        warehouseDefaultStorageToDto(values),
        { signal },
      );
    return warehouseDefaultStorageFromDto(data);
  } catch (cause: unknown) {
    if (isCancel(cause)) throw cause;
    const status = getApiErrorStatus(cause);
    const detail: unknown = isAxiosError(cause)
      ? cause.response?.data?.detail
      : undefined;
    const fields: WarehouseDefaultStorageFieldErrors = {};
    if (
      status === 422 &&
      Array.isArray(detail) &&
      detail.some(
        (issue) =>
          typeof issue === "object" &&
          issue !== null &&
          Array.isArray(issue.loc) &&
          issue.loc[1] === "location_id",
      )
    )
      fields.locationId = "Выберите локацию хранения.";
    throw new WarehouseDefaultStorageRequestError(
      status === 403
        ? "Нет доступа к настройке основной локации."
        : status === 404
          ? "Склад или выбранная локация не найдены."
          : getApiErrorMessage(cause, "Не удалось назначить основную локацию."),
      status,
      fields,
    );
  }
}
