import { computed, type Ref } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { patchStockLotDates } from "../api/stock-lot.api";
import { stockLotKeys } from "./stock-lot.query-keys";
import { invalidateStockLotDateViews } from "./stock-lot-date-dependencies";
import { StockLotRequestError } from "./stock-lot.errors";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { StockLot, StockLotDatesChanges } from "./stock-lot.types";
export interface UpdateStockLotInput {
  scope: InventoryScope;
  itemId: string;
  lotId: string;
  changes: StockLotDatesChanges;
  signal: AbortSignal;
}
export function useUpdateStockLot(
  itemId: Ref<string>,
  lotId: Ref<string>,
  scope: InventoryScopeState,
): UseMutationReturnType<StockLot, Error, UpdateStockLotInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: UpdateStockLotInput): boolean =>
    scope.ready.value &&
    itemId.value === input.itemId &&
    lotId.value === input.lotId &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() =>
      stockLotKeys.update(scope.key.value, itemId.value, lotId.value),
    ),
    retry: false,
    mutationFn: (input: UpdateStockLotInput): Promise<StockLot> => {
      if (!relevant(input)) throw new Error("Контекст партии изменился.");
      return patchStockLotDates(
        input.itemId,
        input.lotId,
        input.changes,
        input.signal,
      );
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      const key = stockLotKeys.detail(input.scope, input.itemId, input.lotId);
      await cache.cancelQueries({ queryKey: key, exact: true });
      if (!relevant(input)) return;
      cache.setQueryData(key, result);
      await invalidateStockLotDateViews(
        cache,
        input.scope,
        input.itemId,
        input.lotId,
      );
    },
    onError: async (error, input) => {
      if (!relevant(input)) return;
      if (
        error instanceof StockLotRequestError &&
        [403, 404].includes(error.status ?? 0)
      ) {
        const key = stockLotKeys.detail(input.scope, input.itemId, input.lotId);
        await cache.cancelQueries({ queryKey: key, exact: true });
        if (!relevant(input)) return;
        cache.removeQueries({ queryKey: key, exact: true });
      }
      if (relevant(input))
        await invalidateStockLotDateViews(
          cache,
          input.scope,
          input.itemId,
          input.lotId,
        );
    },
  });
}
