import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { cancelWriteOff } from "../api/write-off.api";
import { writeOffKeys } from "./write-off.query-keys";
import { newestWriteOff } from "./write-off-edit";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type {
  WriteOffDocument,
  WriteOffVersionValues,
} from "./write-off.types";
export interface CancelWriteOffInput {
  id: string;
  values: WriteOffVersionValues;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useCancelWriteOff(
  scope: InventoryScopeState,
): UseMutationReturnType<
  WriteOffDocument,
  Error,
  CancelWriteOffInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: CancelWriteOffInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => writeOffKeys.cancel(scope.key.value)),
    retry: false,
    mutationFn: (input: CancelWriteOffInput): Promise<WriteOffDocument> => {
      if (!relevant(input)) throw new Error("Контекст списания изменился.");
      return cancelWriteOff(input.id, input.values, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.cancelQueries({
        queryKey: writeOffKeys.detail(input.scope, result.id),
        exact: true,
      });
      if (!relevant(input)) return;
      cache.setQueryData<WriteOffDocument>(
        writeOffKeys.detail(input.scope, result.id),
        (current) => newestWriteOff(current, result),
      );
      await cache.invalidateQueries({
        queryKey: writeOffKeys.lists(input.scope),
      });
    },
  });
}
