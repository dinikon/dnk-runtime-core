import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { createPackagingType } from "../api/packaging-type.api";
import type {
  PackagingType,
  PackagingTypeCreateValues,
} from "./packaging-type.types";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { packagingTypeKeys } from "./packaging-type.query-keys";

export interface CreatePackagingTypeInput {
  values: PackagingTypeCreateValues;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useCreatePackagingType(
  scope: InventoryScopeState,
): UseMutationReturnType<
  PackagingType,
  Error,
  CreatePackagingTypeInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: CreatePackagingTypeInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => packagingTypeKeys.create(scope.key.value)),
    retry: false,
    mutationFn: (input: CreatePackagingTypeInput) => {
      if (!relevant(input)) throw new Error("Контекст типа тары изменился.");
      return createPackagingType(input.values, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.cancelQueries({
        queryKey: packagingTypeKeys.detail(input.scope, result.id),
        exact: true,
      });
      if (!relevant(input)) return;
      cache.setQueryData(
        packagingTypeKeys.detail(input.scope, result.id),
        result,
      );
      await Promise.all([
        cache.invalidateQueries({
          queryKey: packagingTypeKeys.lists(input.scope),
        }),
        cache.invalidateQueries({
          queryKey: packagingTypeKeys.candidateSearches(input.scope),
        }),
      ]);
    },
  });
}
