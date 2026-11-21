import { isCancel } from "axios";
import {
  httpClient,
  getApiErrorMessage,
  getApiErrorStatus,
} from "@/app/providers/http";
import type {
  InventoryItemsListParams,
  InventoryItemsPage,
} from "../model/inventory-item.types";
import { InventoryItemsRequestError } from "../model/inventory-item.errors";
import type { ListInventoryItemsResponseDTO } from "./inventory-item.dto";
import {
  inventoryItemsPageFromDto,
  inventoryItemsParamsToDto,
} from "./inventory-item.mapper";

export async function listInventoryItems(
  params: InventoryItemsListParams,
  signal?: AbortSignal,
): Promise<InventoryItemsPage> {
  try {
    const { data } = await httpClient.get<ListInventoryItemsResponseDTO>(
      "/console/inventory/items",
      {
        params: inventoryItemsParamsToDto(params),
        signal,
      },
    );
    return inventoryItemsPageFromDto(data);
  } catch (error: unknown) {
    if (isCancel(error)) throw error;
    const status = getApiErrorStatus(error);
    throw new InventoryItemsRequestError(
      status === 403
        ? "Нет доступа к складской номенклатуре."
        : getApiErrorMessage(
            error,
            "Не удалось загрузить складскую номенклатуру.",
          ),
      status,
    );
  }
}
