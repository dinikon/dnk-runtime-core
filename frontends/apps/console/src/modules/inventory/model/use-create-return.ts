import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { createReturn } from "../api/return.api";
import { returnKeys } from "./return.query-keys";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type { ReturnDocument, ReturnDraftValues } from "./return.types";
export interface CreateReturnInput {
  values: ReturnDraftValues;
  key: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useCreateReturn(
  scope: InventoryScopeState,
): UseMutationReturnType<ReturnDocument, Error, CreateReturnInput, unknown> {
  const cache = useQueryClient();
  const relevant = (i: CreateReturnInput): boolean =>
    scope.ready.value &&
    !i.signal.aborted &&
    i.scope.every((v, n) => v === scope.key.value[n]);
  return useMutation({
    mutationKey: computed(() => returnKeys.create(scope.key.value)),
    retry: false,
    mutationFn: (input: CreateReturnInput) => {
      if (!relevant(input)) throw new Error("Контекст возврата изменился.");
      return createReturn(input.values, input.key, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      // Ответ идемпотентного создания может описывать прежнюю версию плана.
      await cache.invalidateQueries({
        queryKey: returnKeys.detail(input.scope, result.id),
        exact: true,
        refetchType: "all",
      });
      if (!relevant(input)) return;
      await cache.invalidateQueries({
        queryKey: returnKeys.lists(input.scope),
      });
    },
  });
}
