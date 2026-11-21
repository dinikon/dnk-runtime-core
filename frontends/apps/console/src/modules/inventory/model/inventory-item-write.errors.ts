import { InventoryItemsRequestError } from "./inventory-item.errors.ts";
import type { InventoryItemChanges } from "./inventory-item-editor.types.ts";
export class InventoryItemWriteError extends InventoryItemsRequestError {
  constructor(
    message: string,
    status: number | null,
    readonly fields: Partial<Record<keyof InventoryItemChanges, string>> = {},
    readonly barcodeIssues: Record<number, string> = {},
  ) {
    super(message, status);
    this.name = "InventoryItemWriteError";
  }
  get uncertain(): boolean {
    return this.status === null || this.status === 408 || this.status >= 500;
  }
}
