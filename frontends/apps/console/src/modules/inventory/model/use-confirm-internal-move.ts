import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { confirmInternalMove } from "../api/internal-move.api";
import { internalMoveKeys } from "./internal-move.query-keys";
import { newestInternalMove } from "./internal-move-edit";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type {
  InternalMoveDocument,
  InternalMoveVersionValues,
} from "./internal-move.types";
export interface ConfirmInternalMoveInput {
  id: string;
  values: InternalMoveVersionValues;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useConfirmInternalMove(
  scope: InventoryScopeState,
): UseMutationReturnType<
  InternalMoveDocument,
  Error,
  ConfirmInternalMoveInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: ConfirmInternalMoveInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => internalMoveKeys.confirm(scope.key.value)),
    retry: false,
    mutationFn: (
      input: ConfirmInternalMoveInput,
    ): Promise<InternalMoveDocument> => {
      if (!relevant(input)) throw new Error("Контекст перемещения изменился.");
      return confirmInternalMove(input.id, input.values, input.signal);
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
