import type {
  StockLocationEditValues,
  StockLocationChanges,
} from "./stock-location.types.ts";
export function stockLocationSnapshot(
  value: StockLocationEditValues,
): StockLocationEditValues {
  return { code: value.code, name: value.name, isActive: value.isActive };
}
export function stockLocationChanges(
  value: StockLocationEditValues,
  baseline: StockLocationEditValues,
): StockLocationChanges {
  const changes: StockLocationChanges = {};
  if (value.code !== baseline.code) changes.code = value.code;
  if (value.name !== baseline.name) changes.name = value.name;
  if (value.isActive !== baseline.isActive) changes.isActive = value.isActive;
  return changes;
}
export class StockLocationDraft {
  values: StockLocationEditValues | null = null;
  private baseline: StockLocationEditValues | null = null;
  get changes(): StockLocationChanges {
    return this.values && this.baseline
      ? stockLocationChanges(this.values, this.baseline)
      : {};
  }
  get dirty(): boolean {
    return Object.keys(this.changes).length > 0;
  }
  receive(value: StockLocationEditValues): void {
    if (!this.dirty) this.reset(value);
  }
  change(value: StockLocationEditValues): void {
    this.values = stockLocationSnapshot(value);
  }
  reset(value: StockLocationEditValues): void {
    this.values = stockLocationSnapshot(value);
    this.baseline = stockLocationSnapshot(value);
  }
  clear(): void {
    this.values = null;
    this.baseline = null;
  }
  acknowledge(
    sent: StockLocationEditValues,
    result: StockLocationEditValues,
  ): void {
    if (!this.values) return;
    const current = this.values;
    this.values = {
      code: current.code === sent.code ? result.code : current.code,
      name: current.name === sent.name ? result.name : current.name,
      isActive:
        current.isActive === sent.isActive ? result.isActive : current.isActive,
    };
    this.baseline = stockLocationSnapshot(result);
  }
}
