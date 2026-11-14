import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { patchSupplierSource } from "../api/supplier-source.api";
import type {
  SupplierSource,
  SourceChanges,
  SupplierScope,
} from "./supplier-source.types";
import type { SupplierScopeState } from "./use-supplier-scope";
import { sourceKeys } from "./supplier-source.query-keys";
export interface UpdateSourceInput {
  id: string;
  changes: SourceChanges;
  scope: SupplierScope;
  signal: AbortSignal;
}
export function useUpdateSupplierSource(
  scope: SupplierScopeState,
): UseMutationReturnType<SupplierSource, Error, UpdateSourceInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: UpdateSourceInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((value, index) => value === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => sourceKeys.update(scope.key.value)),
    retry: false,
    mutationFn: (input: UpdateSourceInput) => {
      if (!relevant(input)) throw new Error("Контекст источника изменился.");
      return patchSupplierSource(input.id, input.changes, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.cancelQueries({
        queryKey: sourceKeys.detail(input.scope, result.id),
        exact: true,
      });
      if (!relevant(input)) return;
      cache.setQueryData(sourceKeys.detail(input.scope, result.id), result);
      await cache.invalidateQueries({
        queryKey: sourceKeys.lists(input.scope),
      });
    },
  });
}
