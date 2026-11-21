import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { listPackagingTypes } from "../api/packaging-type.api";
import { packagingTypeKeys } from "./packaging-type.query-keys";
import { retryPackagingTypes } from "./packaging-type.errors";
import type {
  PackagingTypesListParams,
  PackagingTypesPage,
} from "./packaging-type.types";
import type { InventoryScopeState } from "./use-inventory-scope";

export function usePackagingTypesQuery(
  params: Ref<PackagingTypesListParams>,
  scope: InventoryScopeState,
): UseQueryReturnType<PackagingTypesPage, Error> {
  return useQuery({
    queryKey: computed(() =>
      packagingTypeKeys.list(scope.key.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) => listPackagingTypes(queryKey[6], signal),
    enabled: scope.ready,
    staleTime: 30_000,
    retry: retryPackagingTypes,
  });
}
