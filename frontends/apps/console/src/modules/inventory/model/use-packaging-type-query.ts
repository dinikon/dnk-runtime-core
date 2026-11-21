import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { getPackagingType } from "../api/packaging-type.api";
import { packagingTypeKeys } from "./packaging-type.query-keys";
import { retryPackagingTypes } from "./packaging-type.errors";
import type { PackagingType } from "./packaging-type.types";
import type { InventoryScopeState } from "./use-inventory-scope";

export function usePackagingTypeQuery(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<PackagingType, Error> {
  return useQuery({
    queryKey: computed(() =>
      packagingTypeKeys.detail(scope.key.value, id.value),
    ),
    queryFn: ({ queryKey, signal }) => getPackagingType(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 30_000,
    retry: retryPackagingTypes,
  });
}
