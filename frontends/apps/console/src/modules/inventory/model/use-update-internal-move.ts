import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { patchInternalMove } from "../api/internal-move.api";
import { internalMoveKeys } from "./internal-move.query-keys";
import { newestInternalMove } from "./internal-move-edit";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type {
  InternalMoveDocument,
  InternalMoveEditValues,
} from "./internal-move.types";
export interface UpdateInternalMoveInput {
  id: string;
  values: InternalMoveEditValues;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useUpdateInternalMove(
  scope: InventoryScopeState,
): UseMutationReturnType<
  InternalMoveDocument,
  Error,
  UpdateInternalMoveInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: UpdateInternalMoveInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => internalMoveKeys.update(scope.key.value)),
    retry: false,
    mutationFn: (
      input: UpdateInternalMoveInput,
    ): Promise<InternalMoveDocument> => {
      if (!relevant(input)) throw new Error("Контекст перемещения изменился.");
      return patchInternalMove(input.id, input.values, input.signal);
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
