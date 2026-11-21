import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { listInventoryItems } from "../api/inventory-item.api";
import { inventoryItemKeys } from "./inventory-item.query-keys";
import { retryInventoryItems } from "./inventory-item.errors";
import type {
  InventoryItemsListParams,
  InventoryItemsPage,
} from "./inventory-item.types";
import type { InventoryScopeState } from "./use-inventory-scope";

export function useInventoryItemsQuery(
  params: Ref<InventoryItemsListParams>,
  scope: InventoryScopeState,
): UseQueryReturnType<InventoryItemsPage, Error> {
  return useQuery({
    queryKey: computed(() =>
      inventoryItemKeys.list(scope.key.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) => listInventoryItems(queryKey[6], signal),
    enabled: scope.ready,
    staleTime: 30_000,
    retry: retryInventoryItems,
  });
}
