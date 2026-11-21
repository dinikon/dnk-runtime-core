import { isAxiosError, isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type { InventoryItemDetails } from "../model/inventory-item-settings.types";
import type { InventoryItemChanges } from "../model/inventory-item-editor.types";
import { InventoryItemWriteError } from "../model/inventory-item-write.errors";
import type { PatchInventoryItemResponseDTO } from "./inventory-item-settings.dto";
import { inventoryItemDetailsFromDto } from "./inventory-item-settings.mapper";
import { inventoryItemChangesToDto } from "./inventory-item-edit.mapper";
function requestError(cause: unknown, fallback: string): never {
  if (isCancel(cause)) throw cause;
  const status = getApiErrorStatus(cause),
    fields: Partial<Record<keyof InventoryItemChanges, string>> = {},
    barcodeIssues: Record<number, string> = {};
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
      if (field === "barcodes") {
        const index: unknown = issue.loc[2];
        if (typeof index === "number")
          barcodeIssues[index] = "Проверьте значение штрихкода.";
        else fields.barcodes = "Проверьте список штрихкодов.";
      }
      if (field === "sku") fields.sku = "Проверьте код SKU.";
      if (field === "base_uom") fields.baseUom = "Выберите единицу измерения.";
      if (field === "quantity_rules")
        fields.quantityStep = "Проверьте шаг количества.";
      if (field === "tracking_mode")
        fields.trackingMode = "Выберите режим прослеживаемости.";
      if (field === "expiration_mode")
        fields.expirationMode = "Выберите режим срока годности.";
    }
  throw new InventoryItemWriteError(
    status === 403
      ? "Нет доступа к складской позиции."
      : status === 404
        ? "Складская позиция не найдена."
        : getApiErrorMessage(cause, fallback),
    status,
    fields,
    barcodeIssues,
  );
}
function resource(id: string): string {
  return `/console/inventory/items/${encodeURIComponent(id)}`;
}
export async function patchInventoryItem(
  id: string,
  changes: InventoryItemChanges,
  signal?: AbortSignal,
): Promise<InventoryItemDetails> {
  try {
    const { data } = await httpClient.patch<PatchInventoryItemResponseDTO>(
      resource(id),
      inventoryItemChangesToDto(changes),
      { signal },
    );
    return inventoryItemDetailsFromDto(data);
  } catch (cause: unknown) {
    return requestError(
      cause,
      "Не удалось сохранить карточку. Ваш ввод сохранён.",
    );
  }
}
export async function deleteInventoryItem(
  id: string,
  signal?: AbortSignal,
): Promise<void> {
  try {
    await httpClient.delete<void>(resource(id), { signal });
  } catch (cause: unknown) {
    requestError(cause, "Не удалось удалить складскую позицию.");
  }
}
