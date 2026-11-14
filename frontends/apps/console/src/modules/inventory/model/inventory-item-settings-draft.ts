import type { InventoryItemSettings } from "./inventory-item-settings.types.ts";

export const inventorySettingsFields = [
  "baseUom",
  "quantityStep",
  "trackingMode",
  "expirationMode",
] as const;

export function inventorySettingsSnapshot(
  value: InventoryItemSettings,
): InventoryItemSettings {
  return {
    baseUom: value.baseUom,
    quantityStep: value.quantityStep,
    trackingMode: value.trackingMode,
    expirationMode: value.expirationMode,
  };
}
