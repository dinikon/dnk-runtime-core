import { InventoryItemsRequestError } from "./inventory-item.errors.ts";

export class InventoryItemCreateError extends InventoryItemsRequestError {
  get uncertain(): boolean {
    return this.status === null || this.status >= 500;
  }
}
