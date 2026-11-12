import type {
  WarehouseEditValues,
  WarehouseChanges,
} from "./warehouse.types.ts";
export function warehouseSnapshot(
  value: WarehouseEditValues,
): WarehouseEditValues {
  return { code: value.code, name: value.name, isActive: value.isActive };
}
export function warehouseChanges(
  value: WarehouseEditValues,
  baseline: WarehouseEditValues,
): WarehouseChanges {
  const changes: WarehouseChanges = {};
  if (value.code !== baseline.code) changes.code = value.code;
  if (value.name !== baseline.name) changes.name = value.name;
  if (value.isActive !== baseline.isActive) changes.isActive = value.isActive;
  return changes;
}
export class WarehouseDraft {
  values: WarehouseEditValues | null = null;
  private baseline: WarehouseEditValues | null = null;
  get changes(): WarehouseChanges {
    return this.values && this.baseline
      ? warehouseChanges(this.values, this.baseline)
      : {};
  }
  get dirty(): boolean {
    return Object.keys(this.changes).length > 0;
  }
  receive(value: WarehouseEditValues): void {
    if (!this.dirty) this.reset(value);
  }
  change(value: WarehouseEditValues): void {
    this.values = warehouseSnapshot(value);
  }
  reset(value: WarehouseEditValues): void {
    this.values = warehouseSnapshot(value);
    this.baseline = warehouseSnapshot(value);
  }
  clear(): void {
    this.values = null;
    this.baseline = null;
  }
  acknowledge(sent: WarehouseEditValues, result: WarehouseEditValues): void {
    if (!this.values) return;
    const current = this.values;
    this.values = {
      code: current.code === sent.code ? result.code : current.code,
      name: current.name === sent.name ? result.name : current.name,
      isActive:
        current.isActive === sent.isActive ? result.isActive : current.isActive,
    };
    this.baseline = warehouseSnapshot(result);
  }
}
