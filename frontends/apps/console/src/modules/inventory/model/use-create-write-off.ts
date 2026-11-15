import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { createWriteOff } from "../api/write-off.api";
import { writeOffKeys } from "./write-off.query-keys";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type { WriteOffDocument, WriteOffDraftValues } from "./write-off.types";
export interface CreateWriteOffInput {
  values: WriteOffDraftValues;
  key: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useCreateWriteOff(
  scope: InventoryScopeState,
): UseMutationReturnType<
  WriteOffDocument,
  Error,
  CreateWriteOffInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (i: CreateWriteOffInput): boolean =>
    scope.ready.value &&
    !i.signal.aborted &&
    i.scope.every((v, n) => v === scope.key.value[n]);
  return useMutation({
    mutationKey: computed(() => writeOffKeys.create(scope.key.value)),
    retry: false,
    mutationFn: (input: CreateWriteOffInput) => {
      if (!relevant(input)) throw new Error("Контекст списания изменился.");
      return createWriteOff(input.values, input.key, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      // Ответ идемпотентного создания может описывать прежнюю версию плана.
      await cache.invalidateQueries({
        queryKey: writeOffKeys.detail(input.scope, result.id),
        exact: true,
        refetchType: "all",
      });
      if (!relevant(input)) return;
      await cache.invalidateQueries({
        queryKey: writeOffKeys.lists(input.scope),
      });
    },
  });
}
