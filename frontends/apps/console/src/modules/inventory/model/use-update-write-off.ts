import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { patchWriteOff } from "../api/write-off.api";
import { writeOffKeys } from "./write-off.query-keys";
import { newestWriteOff } from "./write-off-edit";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type { WriteOffDocument, WriteOffEditValues } from "./write-off.types";
export interface UpdateWriteOffInput {
  id: string;
  values: WriteOffEditValues;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useUpdateWriteOff(
  scope: InventoryScopeState,
): UseMutationReturnType<
  WriteOffDocument,
  Error,
  UpdateWriteOffInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: UpdateWriteOffInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => writeOffKeys.update(scope.key.value)),
    retry: false,
    mutationFn: (input: UpdateWriteOffInput): Promise<WriteOffDocument> => {
      if (!relevant(input)) throw new Error("Контекст списания изменился.");
      return patchWriteOff(input.id, input.values, input.signal);
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
