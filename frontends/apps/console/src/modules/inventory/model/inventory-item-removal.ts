import { stockLotKeys } from "./stock-lot.query-keys.ts";
import type { QueryClient } from "@tanstack/vue-query";
import { inventoryItemKeys } from "./inventory-item.query-keys.ts";
import { itemPackagingKeys } from "./item-packaging.query-keys.ts";
import type { InventoryItemsPage } from "./inventory-item.types.ts";
import type { InventoryItemMutationInput } from "./inventory-item-editor.types.ts";
export function withoutInventoryItem(
  page: InventoryItemsPage | undefined,
  id: string,
): InventoryItemsPage | undefined {
  if (!page?.items.some((item) => item.id === id)) return page;
  return {
    ...page,
    items: page.items.filter((item) => item.id !== id),
    total: Math.max(0, page.total - 1),
  };
}
export async function forgetInventoryItem(
  cache: QueryClient,
  input: InventoryItemMutationInput,
  relevant: () => boolean,
): Promise<void> {
  if (!relevant()) return;
  const detail = inventoryItemKeys.detail(input.scope, input.id),
    lists = inventoryItemKeys.lists(input.scope),
    packaging = itemPackagingKeys.root(input.scope, input.id),
    lots = stockLotKeys.root(input.scope, input.id);
  await Promise.all([
    cache.cancelQueries({ queryKey: detail, exact: true }),
    cache.cancelQueries({ queryKey: lists }),
    cache.cancelQueries({ queryKey: packaging }),
    cache.cancelQueries({ queryKey: lots }),
  ]);
  if (!relevant()) return;
  cache.removeQueries({ queryKey: detail, exact: true });
  cache.removeQueries({ queryKey: packaging });
  cache.removeQueries({ queryKey: lots });
  cache.setQueriesData<InventoryItemsPage>({ queryKey: lists }, (page) =>
    withoutInventoryItem(page, input.id),
  );
  await cache.invalidateQueries({ queryKey: lists, refetchType: "none" });
}
export async function discardInaccessibleInventoryItem(
  cache: QueryClient,
  input: InventoryItemMutationInput,
  relevant: () => boolean,
): Promise<void> {
  if (!relevant()) return;
  const detail = inventoryItemKeys.detail(input.scope, input.id),
    lists = inventoryItemKeys.lists(input.scope),
    packaging = itemPackagingKeys.root(input.scope, input.id),
    lots = stockLotKeys.root(input.scope, input.id);
  await Promise.all([
    cache.cancelQueries({ queryKey: detail, exact: true }),
    cache.cancelQueries({ queryKey: lists }),
    cache.cancelQueries({ queryKey: packaging }),
    cache.cancelQueries({ queryKey: lots }),
  ]);
  if (!relevant()) return;
  cache.removeQueries({ queryKey: detail, exact: true });
  cache.removeQueries({ queryKey: lists });
  cache.removeQueries({ queryKey: packaging });
  cache.removeQueries({ queryKey: lots });
}
