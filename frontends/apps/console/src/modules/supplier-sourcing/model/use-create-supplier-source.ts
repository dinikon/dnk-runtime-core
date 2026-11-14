import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { createSupplierSource } from "../api/supplier-source.api";
import type {
  SupplierSource,
  SourceValues,
  SupplierScope,
} from "./supplier-source.types";
import type { SupplierScopeState } from "./use-supplier-scope";
import { sourceKeys } from "./supplier-source.query-keys";
export interface CreateSourceInput {
  values: SourceValues;
  scope: SupplierScope;
  signal: AbortSignal;
}
export function useCreateSupplierSource(
  scope: SupplierScopeState,
): UseMutationReturnType<SupplierSource, Error, CreateSourceInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: CreateSourceInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((value, index) => value === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => sourceKeys.create(scope.key.value)),
    retry: false,
    mutationFn: (input: CreateSourceInput) => {
      if (!relevant(input)) throw new Error("Контекст источника изменился.");
      return createSupplierSource(input.values, input.signal);
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
