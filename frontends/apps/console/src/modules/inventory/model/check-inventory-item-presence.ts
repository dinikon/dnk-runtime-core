import { getInventoryItem } from "../api/inventory-item-settings.api";
import { InventorySettingsRequestError } from "./inventory-item-settings.errors";
import type { InventoryItemMutationInput } from "./inventory-item-editor.types";
import type { InventoryItemDetails } from "./inventory-item-settings.types";
/** Читает свежий корень без кеша и повторов после неоднозначного DELETE. */
export async function checkInventoryItemPresence(
  input: InventoryItemMutationInput,
): Promise<InventoryItemDetails | null> {
  try {
    return await getInventoryItem(input.id, input.signal);
  } catch (cause: unknown) {
    if (cause instanceof InventorySettingsRequestError && cause.status === 404)
      return null;
    throw cause;
  }
}
