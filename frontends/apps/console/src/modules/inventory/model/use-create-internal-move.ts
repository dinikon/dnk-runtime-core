import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { createInternalMove } from "../api/internal-move.api";
import { internalMoveKeys } from "./internal-move.query-keys";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type {
  InternalMoveDocument,
  InternalMoveDraftValues,
} from "./internal-move.types";
export interface CreateInternalMoveInput {
  values: InternalMoveDraftValues;
  key: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useCreateInternalMove(
  scope: InventoryScopeState,
): UseMutationReturnType<
  InternalMoveDocument,
  Error,
  CreateInternalMoveInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (i: CreateInternalMoveInput): boolean =>
    scope.ready.value &&
    !i.signal.aborted &&
    i.scope.every((v, n) => v === scope.key.value[n]);
  return useMutation({
    mutationKey: computed(() => internalMoveKeys.create(scope.key.value)),
    retry: false,
    mutationFn: (input: CreateInternalMoveInput) => {
      if (!relevant(input)) throw new Error("Контекст перемещения изменился.");
      return createInternalMove(input.values, input.key, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      // Ответ идемпотентного создания может описывать прежнюю версию плана.
      await cache.invalidateQueries({
        queryKey: internalMoveKeys.detail(input.scope, result.id),
        exact: true,
        refetchType: "all",
      });
      if (!relevant(input)) return;
      await cache.invalidateQueries({
        queryKey: internalMoveKeys.lists(input.scope),
      });
    },
  });
}
