import { computed, type Ref } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { createStockLot } from "../api/stock-lot.api";
import { stockLotKeys } from "./stock-lot.query-keys";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { StockLot, StockLotValues } from "./stock-lot.types";
export interface CreateStockLotInput {
  itemId: string;
  scope: InventoryScope;
  values: StockLotValues;
  signal: AbortSignal;
}
export function useCreateStockLot(
  itemId: Ref<string>,
  scope: InventoryScopeState,
): UseMutationReturnType<StockLot, Error, CreateStockLotInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: CreateStockLotInput): boolean =>
    scope.ready.value &&
    itemId.value === input.itemId &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() =>
      stockLotKeys.create(scope.key.value, itemId.value),
    ),
    retry: false,
    mutationFn: (input: CreateStockLotInput): Promise<StockLot> => {
      if (!relevant(input)) throw new Error("Контекст SKU изменился.");
      return createStockLot(input.itemId, input.values, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.cancelQueries({
        queryKey: stockLotKeys.detail(input.scope, input.itemId, result.id),
        exact: true,
      });
      if (!relevant(input)) return;
      cache.setQueryData(
        stockLotKeys.detail(input.scope, input.itemId, result.id),
        result,
      );
      await cache.invalidateQueries({
        queryKey: stockLotKeys.lists(input.scope, input.itemId),
      });
    },
    onError: async (_error, input) => {
      if (relevant(input))
        await cache.invalidateQueries({
          queryKey: stockLotKeys.lists(input.scope, input.itemId),
        });
    },
  });
}
