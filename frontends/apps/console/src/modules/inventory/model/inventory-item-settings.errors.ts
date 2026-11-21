import { InventoryItemsRequestError } from "./inventory-item.errors.ts";
import type { InventorySettingsErrors } from "./inventory-item-settings.types.ts";

export class InventorySettingsRequestError extends InventoryItemsRequestError {
  constructor(
    message: string,
    status: number | null,
    readonly fields: InventorySettingsErrors = {},
  ) {
    super(message, status);
    this.name = "InventorySettingsRequestError";
  }
}
