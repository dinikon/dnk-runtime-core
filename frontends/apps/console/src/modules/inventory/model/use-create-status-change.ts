import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { createStatusChange } from "../api/status-change.api";
import { statusChangeKeys } from "./status-change.query-keys";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type {
  StatusChangeDocument,
  StatusChangeDraftValues,
} from "./status-change.types";
export interface CreateStatusChangeInput {
  values: StatusChangeDraftValues;
  key: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useCreateStatusChange(
  scope: InventoryScopeState,
): UseMutationReturnType<
  StatusChangeDocument,
  Error,
  CreateStatusChangeInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (i: CreateStatusChangeInput): boolean =>
    scope.ready.value &&
    !i.signal.aborted &&
    i.scope.every((v, n) => v === scope.key.value[n]);
  return useMutation({
    mutationKey: computed(() => statusChangeKeys.create(scope.key.value)),
    retry: false,
    mutationFn: (input: CreateStatusChangeInput) => {
      if (!relevant(input))
        throw new Error("Контекст изменения состояния изменился.");
      return createStatusChange(input.values, input.key, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      // Ответ идемпотентного создания может описывать прежнюю версию плана.
      await cache.invalidateQueries({
        queryKey: statusChangeKeys.detail(input.scope, result.id),
        exact: true,
        refetchType: "all",
      });
      if (!relevant(input)) return;
      await cache.invalidateQueries({
        queryKey: statusChangeKeys.lists(input.scope),
      });
    },
  });
}
