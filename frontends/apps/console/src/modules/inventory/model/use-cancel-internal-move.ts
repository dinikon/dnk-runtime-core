import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { cancelInternalMove } from "../api/internal-move.api";
import { internalMoveKeys } from "./internal-move.query-keys";
import { newestInternalMove } from "./internal-move-edit";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type {
  InternalMoveDocument,
  InternalMoveVersionValues,
} from "./internal-move.types";
export interface CancelInternalMoveInput {
  id: string;
  values: InternalMoveVersionValues;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useCancelInternalMove(
  scope: InventoryScopeState,
): UseMutationReturnType<
  InternalMoveDocument,
  Error,
  CancelInternalMoveInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: CancelInternalMoveInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => internalMoveKeys.cancel(scope.key.value)),
    retry: false,
    mutationFn: (
      input: CancelInternalMoveInput,
    ): Promise<InternalMoveDocument> => {
      if (!relevant(input)) throw new Error("Контекст перемещения изменился.");
      return cancelInternalMove(input.id, input.values, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.cancelQueries({
        queryKey: internalMoveKeys.detail(input.scope, result.id),
        exact: true,
      });
      if (!relevant(input)) return;
      cache.setQueryData<InternalMoveDocument>(
        internalMoveKeys.detail(input.scope, result.id),
        (current) => newestInternalMove(current, result),
      );
      await cache.invalidateQueries({
        queryKey: internalMoveKeys.lists(input.scope),
      });
    },
  });
}
