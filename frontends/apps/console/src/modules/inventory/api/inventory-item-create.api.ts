import { isCancel } from "axios";
import {
  httpClient,
  getApiErrorStatus,
  getApiErrorMessage,
} from "@/app/providers/http";
import type { CreateInventoryItemValues } from "../model/inventory-item-create.types";
import type { InventoryItemDetails } from "../model/inventory-item-settings.types";
import { InventoryItemCreateError } from "../model/inventory-item-create.errors";
import type { CreateInventoryItemResponseDTO } from "./inventory-item-create.dto";
import {
  inventoryItemCreateToDto,
  inventoryItemCreatedFromDto,
} from "./inventory-item-create.mapper";

export async function createInventoryItem(
  value: CreateInventoryItemValues,
  signal?: AbortSignal,
): Promise<InventoryItemDetails> {
  try {
    const { data } = await httpClient.post<CreateInventoryItemResponseDTO>(
      "/console/inventory/items",
      inventoryItemCreateToDto(value),
      { signal },
    );
    return inventoryItemCreatedFromDto(data);
  } catch (cause: unknown) {
    if (isCancel(cause)) throw cause;
    const status = getApiErrorStatus(cause);
    throw new InventoryItemCreateError(
      status === 403
        ? "Нет доступа к созданию складских позиций."
        : getApiErrorMessage(
            cause,
            status === 422
              ? "Проверьте код SKU."
              : "Не удалось создать складскую позицию.",
          ),
      status,
    );
  }
}
