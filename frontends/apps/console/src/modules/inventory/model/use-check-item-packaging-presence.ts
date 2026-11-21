import { getInventoryItem } from "../api/inventory-item-settings.api";
import { getItemPackaging } from "../api/item-packaging.api";
import { ItemPackagingRequestError } from "./item-packaging.errors";
import type { DeleteItemPackagingInput } from "./item-packaging-removal";
import type { ItemPackaging } from "./item-packaging.types";

/** Свежие последовательные чтения без кеша и повторов: 404 упаковки неоднозначен без SKU. */
export async function checkItemPackagingPresence(
  input: DeleteItemPackagingInput,
): Promise<ItemPackaging | null> {
  await getInventoryItem(input.itemId, input.signal);
  try {
    return await getItemPackaging(input.itemId, input.id, input.signal);
  } catch (cause: unknown) {
    if (cause instanceof ItemPackagingRequestError && cause.status === 404)
      return null;
    throw cause;
  }
}
