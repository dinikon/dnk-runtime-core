import type { StockLocation } from "./stock-location.types.ts";

export class DefaultStorageLocationDraft {
  selectedId: string | null = null;
  private baseline: string | null = null;

  get dirty(): boolean {
    return this.selectedId !== this.baseline;
  }

  reset(id: string | null): void {
    this.selectedId = id;
    this.baseline = id;
  }

  receive(id: string | null): void {
    if (!this.dirty) this.reset(id);
  }

  change(id: string): void {
    this.selectedId = id;
  }
}

export function isDefaultStorageCandidate(
  location: StockLocation | undefined,
  warehouseId: string,
): boolean {
  return (
    !!location &&
    location.warehouseId === warehouseId &&
    location.isActive &&
    location.locationType === "STORAGE"
  );
}
