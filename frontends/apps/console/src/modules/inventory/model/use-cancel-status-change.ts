import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { cancelStatusChange } from "../api/status-change.api";
import { statusChangeKeys } from "./status-change.query-keys";
import { newestStatusChange } from "./status-change-edit";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type {
  StatusChangeDocument,
  StatusChangeVersionValues,
} from "./status-change.types";
export interface CancelStatusChangeInput {
  id: string;
  values: StatusChangeVersionValues;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useCancelStatusChange(
  scope: InventoryScopeState,
): UseMutationReturnType<
  StatusChangeDocument,
  Error,
  CancelStatusChangeInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: CancelStatusChangeInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => statusChangeKeys.cancel(scope.key.value)),
    retry: false,
    mutationFn: (
      input: CancelStatusChangeInput,
    ): Promise<StatusChangeDocument> => {
      if (!relevant(input))
        throw new Error("Контекст изменения состояния изменился.");
      return cancelStatusChange(input.id, input.values, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.cancelQueries({
        queryKey: statusChangeKeys.detail(input.scope, result.id),
        exact: true,
      });
      if (!relevant(input)) return;
      cache.setQueryData<StatusChangeDocument>(
        statusChangeKeys.detail(input.scope, result.id),
        (current) => newestStatusChange(current, result),
      );
      await cache.invalidateQueries({
        queryKey: statusChangeKeys.lists(input.scope),
      });
    },
  });
}
