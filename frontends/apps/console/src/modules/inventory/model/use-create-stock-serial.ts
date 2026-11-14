import { computed, type Ref } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { createStockSerial } from "../api/stock-serial.api";
import { stockSerialKeys } from "./stock-serial.query-keys";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { StockSerial, StockSerialValues } from "./stock-serial.types";
export interface CreateStockSerialInput {
  itemId: string;
  scope: InventoryScope;
  values: StockSerialValues;
  signal: AbortSignal;
}
export function useCreateStockSerial(
  itemId: Ref<string>,
  scope: InventoryScopeState,
): UseMutationReturnType<StockSerial, Error, CreateStockSerialInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: CreateStockSerialInput): boolean =>
    scope.ready.value &&
    itemId.value === input.itemId &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() =>
      stockSerialKeys.create(scope.key.value, itemId.value),
    ),
    retry: false,
    mutationFn: (input: CreateStockSerialInput): Promise<StockSerial> => {
      if (!relevant(input)) throw new Error("Контекст SKU изменился.");
      return createStockSerial(input.itemId, input.values, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.cancelQueries({
        queryKey: stockSerialKeys.detail(input.scope, input.itemId, result.id),
        exact: true,
      });
      if (!relevant(input)) return;
      cache.setQueryData(
        stockSerialKeys.detail(input.scope, input.itemId, result.id),
        result,
      );
      await cache.invalidateQueries({
        queryKey: stockSerialKeys.lists(input.scope, input.itemId),
      });
    },
    onError: async (_error, input) => {
      if (relevant(input))
        await cache.invalidateQueries({
          queryKey: stockSerialKeys.lists(input.scope, input.itemId),
        });
    },
  });
}
