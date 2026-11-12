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

export class InventorySettingsDraft {
  values: InventoryItemSettings | null = null;
  private baseline: InventoryItemSettings | null = null;

  get dirty(): boolean {
    return (
      !!this.values &&
      !!this.baseline &&
      inventorySettingsFields.some(
        (field) => this.values![field] !== this.baseline![field],
      )
    );
  }

  receive(value: InventoryItemSettings): void {
    if (!this.dirty) this.reset(value);
  }

  change(value: InventoryItemSettings): void {
    this.values = inventorySettingsSnapshot(value);
  }

  reset(value: InventoryItemSettings): void {
    this.baseline = inventorySettingsSnapshot(value);
    this.values = inventorySettingsSnapshot(value);
  }

  acknowledge(
    sent: InventoryItemSettings,
    result: InventoryItemSettings,
  ): void {
    if (!this.values) return;
    // Only acknowledge each submitted value; preserve edits made while awaiting HTTP.
    const current = this.values;
    this.values = {
      baseUom:
        current.baseUom === sent.baseUom ? result.baseUom : current.baseUom,
      quantityStep:
        current.quantityStep === sent.quantityStep
          ? result.quantityStep
          : current.quantityStep,
      trackingMode:
        current.trackingMode === sent.trackingMode
          ? result.trackingMode
          : current.trackingMode,
      expirationMode:
        current.expirationMode === sent.expirationMode
          ? result.expirationMode
          : current.expirationMode,
    };
    this.baseline = inventorySettingsSnapshot(result);
  }

  clear(): void {
    this.values = null;
    this.baseline = null;
  }
}
