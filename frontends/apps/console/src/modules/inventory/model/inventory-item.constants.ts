import type {
  InventoryExpirationMode,
  InventoryTrackingMode,
} from "./inventory-item.types.ts";

export const INVENTORY_PAGE_SIZE = 50;
export const INVENTORY_PAGE_SIZES = [20, 50, 100] as const;
export const INVENTORY_SEARCH_DELAY = 300;
export const INVENTORY_MAX_OFFSET = 2147483600;

export const inventoryTrackingLabels: Record<InventoryTrackingMode, string> = {
  NONE: "Без прослеживаемости",
  LOT: "По партиям",
  SERIAL: "По сериям",
  LOT_AND_SERIAL: "По партиям и сериям",
};

export const inventoryExpirationLabels: Record<
  InventoryExpirationMode,
  string
> = {
  NONE: "Не учитывается",
  OPTIONAL: "Необязательная заметка",
  REQUIRED: "Обязательный срок",
};
