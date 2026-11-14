import { computed, type Ref } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { patchStockSerial } from "../api/stock-serial.api";
import { stockSerialKeys } from "./stock-serial.query-keys";
import { StockSerialRequestError } from "./stock-serial.errors";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { StockSerial, StockSerialChanges } from "./stock-serial.types";
export interface UpdateStockSerialInput {
  scope: InventoryScope;
  itemId: string;
  serialId: string;
  changes: StockSerialChanges;
  signal: AbortSignal;
}
export function useUpdateStockSerial(
  itemId: Ref<string>,
  serialId: Ref<string>,
  scope: InventoryScopeState,
): UseMutationReturnType<StockSerial, Error, UpdateStockSerialInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: UpdateStockSerialInput): boolean =>
    scope.ready.value &&
    itemId.value === input.itemId &&
    serialId.value === input.serialId &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() =>
      stockSerialKeys.update(scope.key.value, itemId.value, serialId.value),
    ),
    retry: false,
    mutationFn: (input: UpdateStockSerialInput): Promise<StockSerial> => {
      if (!relevant(input)) throw new Error("Контекст экземпляра изменился.");
      return patchStockSerial(
        input.itemId,
        input.serialId,
        input.changes,
        input.signal,
      );
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      const key = stockSerialKeys.detail(
        input.scope,
        input.itemId,
        input.serialId,
      );
      await cache.cancelQueries({ queryKey: key, exact: true });
      if (!relevant(input)) return;
      cache.setQueryData(key, result);
      await cache.invalidateQueries({
        queryKey: stockSerialKeys.lists(input.scope, input.itemId),
      });
    },
    onError: async (error, input) => {
      if (!relevant(input)) return;
      if (error instanceof StockSerialRequestError && error.status === 403) {
        const key = stockSerialKeys.detail(
          input.scope,
          input.itemId,
          input.serialId,
        );
        await cache.cancelQueries({ queryKey: key, exact: true });
        if (!relevant(input)) return;
        cache.removeQueries({ queryKey: key, exact: true });
      }
      if (relevant(input))
        await cache.invalidateQueries({
          queryKey: stockSerialKeys.lists(input.scope, input.itemId),
        });
    },
  });
}
