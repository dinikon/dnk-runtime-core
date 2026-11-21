import { computed, type Ref } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { patchPackagingType } from "../api/packaging-type.api";
import type {
  PackagingType,
  PackagingTypeChanges,
} from "./packaging-type.types";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { packagingTypeKeys } from "./packaging-type.query-keys";

export interface UpdatePackagingTypeInput {
  id: string;
  values: PackagingTypeChanges;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useUpdatePackagingType(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseMutationReturnType<
  PackagingType,
  Error,
  UpdatePackagingTypeInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: UpdatePackagingTypeInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.id === id.value &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() =>
      packagingTypeKeys.update(scope.key.value, id.value),
    ),
    retry: false,
    mutationFn: (input: UpdatePackagingTypeInput) => {
      if (!relevant(input)) throw new Error("Контекст типа тары изменился.");
      return patchPackagingType(input.id, input.values, input.signal);
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
