import type { QueryClient } from "@tanstack/vue-query";
import type { InventoryScope } from "./inventory-scope.types.ts";
import type { ItemPackagingsPage } from "./item-packaging.types.ts";
import { itemPackagingKeys } from "./item-packaging.query-keys.ts";

export interface DeleteItemPackagingInput {
  itemId: string;
  id: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function withoutItemPackaging(
  page: ItemPackagingsPage | undefined,
  id: string,
): ItemPackagingsPage | undefined {
  if (!page?.items.some((item) => item.id === id)) return page;
  return {
    ...page,
    items: page.items.filter((item) => item.id !== id),
    total: Math.max(0, page.total - 1),
  };
}
/** Применяется только после 204 либо подтверждённого отсутствия при существующем SKU. */
export async function forgetItemPackaging(
  cache: QueryClient,
  input: DeleteItemPackagingInput,
  relevant: () => boolean,
): Promise<void> {
  if (!relevant()) return;
  const detail = itemPackagingKeys.detail(input.scope, input.itemId, input.id);
  const lists = itemPackagingKeys.lists(input.scope, input.itemId);
  await Promise.all([
    cache.cancelQueries({ queryKey: detail, exact: true }),
    cache.cancelQueries({ queryKey: lists }),
  ]);
  if (!relevant()) return;
  cache.removeQueries({ queryKey: detail, exact: true });
  cache.setQueriesData<ItemPackagingsPage>({ queryKey: lists }, (page) =>
    withoutItemPackaging(page, input.id),
  );
  // Повторное чтение принадлежит странице: его ошибка не меняет результат DELETE.
  await cache.invalidateQueries({ queryKey: lists, refetchType: "none" });
}

/** Запрещённый контекст не должен снова показываться из свежего кеша при возврате. */
export async function discardItemPackagingContext(
  cache: QueryClient,
  input: DeleteItemPackagingInput,
  relevant: () => boolean,
): Promise<void> {
  if (!relevant()) return;
  const queryKey = itemPackagingKeys.root(input.scope, input.itemId);
  await cache.cancelQueries({ queryKey });
  if (relevant()) cache.removeQueries({ queryKey });
}
