import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { confirmReturn } from "../api/return.api";
import { returnKeys } from "./return.query-keys";
import { newestReturn } from "./return-edit";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type { ReturnDocument, ReturnVersionValues } from "./return.types";
export interface ConfirmReturnInput {
  id: string;
  values: ReturnVersionValues;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useConfirmReturn(
  scope: InventoryScopeState,
): UseMutationReturnType<ReturnDocument, Error, ConfirmReturnInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: ConfirmReturnInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => returnKeys.confirm(scope.key.value)),
    retry: false,
    mutationFn: (input: ConfirmReturnInput): Promise<ReturnDocument> => {
      if (!relevant(input)) throw new Error("Контекст возврата изменился.");
      return confirmReturn(input.id, input.values, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.cancelQueries({
        queryKey: returnKeys.detail(input.scope, result.id),
        exact: true,
      });
      if (!relevant(input)) return;
      cache.setQueryData<ReturnDocument>(
        returnKeys.detail(input.scope, result.id),
        (current) => newestReturn(current, result),
      );
      await cache.invalidateQueries({
        queryKey: returnKeys.lists(input.scope),
      });
    },
  });
}
