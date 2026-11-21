import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { listItemPackagings } from "../api/item-packaging.api";
import { itemPackagingKeys } from "./item-packaging.query-keys";
import { retryItemPackagings } from "./item-packaging.errors";
import type {
  ItemPackagingsListParams,
  ItemPackagingsPage,
} from "./item-packaging.types";
import type { InventoryScopeState } from "./use-inventory-scope";
export function useItemPackagingsQuery(
  itemId: Ref<string>,
  params: Ref<ItemPackagingsListParams>,
  scope: InventoryScopeState,
): UseQueryReturnType<ItemPackagingsPage, Error> {
  return useQuery({
    queryKey: computed(() =>
      itemPackagingKeys.list(scope.key.value, itemId.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listItemPackagings(queryKey[5], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && !!itemId.value),
    staleTime: 30_000,
    retry: retryItemPackagings,
  });
}
