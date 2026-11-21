import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import {
  getInventoryItem,
  listInventoryUoms,
} from "../api/inventory-item-settings.api";
import { inventoryItemKeys } from "./inventory-item.query-keys";
import { retryInventoryItems } from "./inventory-item.errors";
import type {
  InventoryItemDetails,
  InventoryUom,
} from "./inventory-item-settings.types";
import type { InventoryScopeState } from "./use-inventory-scope";

export function useInventoryItemQuery(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<InventoryItemDetails, Error> {
  return useQuery({
    queryKey: computed(() =>
      inventoryItemKeys.detail(scope.key.value, id.value),
    ),
    queryFn: ({ queryKey, signal }) => getInventoryItem(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 30_000,
    retry: retryInventoryItems,
  });
}

export function useInventoryUomsQuery(
  scope: InventoryScopeState,
): UseQueryReturnType<InventoryUom[], Error> {
  return useQuery({
    queryKey: computed(() => inventoryItemKeys.uoms(scope.key.value)),
    queryFn: ({ signal }) => listInventoryUoms(signal),
    enabled: scope.ready,
    staleTime: Infinity,
    retry: retryInventoryItems,
  });
}
