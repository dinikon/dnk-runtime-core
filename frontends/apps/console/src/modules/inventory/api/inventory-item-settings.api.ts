import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import { InventorySettingsRequestError } from "../model/inventory-item-settings.errors";
import type {
  InventoryItemDetails,
  InventoryUom,
  InventorySettingsErrors,
} from "../model/inventory-item-settings.types";
import type {
  GetInventoryItemResponseDTO,
  ListInventoryUomsResponseDTO,
} from "./inventory-item-settings.dto";
import {
  inventoryItemDetailsFromDto,
  inventoryUomsFromDto,
} from "./inventory-item-settings.mapper";

function requestError(cause: unknown, fallback: string): never {
  if (isCancel(cause)) throw cause;
  const status = getApiErrorStatus(cause);
  const fields: InventorySettingsErrors = {};
  const detail: unknown = isAxiosError(cause)
    ? cause.response?.data?.detail
    : undefined;
  if (Array.isArray(detail)) {
    const names = {
      base_uom: "baseUom",
      quantity_rules: "quantityStep",
      tracking_mode: "trackingMode",
      expiration_mode: "expirationMode",
    } as const;
    for (const issue of detail) {
      if (issue && typeof issue === "object" && Array.isArray(issue.loc)) {
        const field = names[issue.loc[1] as keyof typeof names];
        if (field) fields[field] = "Проверьте значение поля.";
      }
    }
  }
  throw new InventorySettingsRequestError(
    status === 403
      ? "Нет доступа к настройкам складского учёта."
      : status === 404
        ? "Складская позиция не найдена."
        : getApiErrorMessage(cause, fallback),
    status,
    fields,
  );
}

export async function getInventoryItem(
  id: string,
  signal?: AbortSignal,
): Promise<InventoryItemDetails> {
  try {
    const { data } = await httpClient.get<GetInventoryItemResponseDTO>(
      `/console/inventory/items/${encodeURIComponent(id)}`,
      { signal },
    );
    return inventoryItemDetailsFromDto(data);
  } catch (cause: unknown) {
    return requestError(cause, "Не удалось загрузить складскую позицию.");
  }
}

export async function listInventoryUoms(
  signal?: AbortSignal,
): Promise<InventoryUom[]> {
  try {
    const { data } = await httpClient.get<ListInventoryUomsResponseDTO>(
      "/console/inventory/uoms",
      { signal },
    );
    return inventoryUomsFromDto(data);
  } catch (cause: unknown) {
    return requestError(cause, "Не удалось загрузить единицы измерения.");
  }
}
