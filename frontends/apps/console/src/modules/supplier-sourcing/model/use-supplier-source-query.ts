import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { SupplierSource } from "./supplier-source.types";
import type { SupplierScopeState } from "./use-supplier-scope";
import { sourceKeys } from "./supplier-source.query-keys";
import { getSupplierSource } from "../api/supplier-source.api";
export function useSupplierSourceQuery(
  id: Ref<string>,
  scope: SupplierScopeState,
): UseQueryReturnType<SupplierSource, Error> {
  return useQuery({
    queryKey: computed(() => sourceKeys.detail(scope.key.value, id.value)),
    queryFn: ({ queryKey, signal }) => getSupplierSource(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 30_000,
    retry: false,
  });
}
