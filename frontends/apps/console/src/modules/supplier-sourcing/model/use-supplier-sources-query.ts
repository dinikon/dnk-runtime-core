import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { SourcesParams, SourcesPage } from "./supplier-source.types";
import type { SupplierScopeState } from "./use-supplier-scope";
import { sourceKeys } from "./supplier-source.query-keys";
import { listSupplierSources } from "../api/supplier-source.api";
export function useSupplierSourcesQuery(
  params: Ref<SourcesParams>,
  scope: SupplierScopeState,
): UseQueryReturnType<SourcesPage, Error> {
  return useQuery({
    queryKey: computed(() => sourceKeys.list(scope.key.value, params.value)),
    queryFn: ({ queryKey, signal }) => listSupplierSources(queryKey[6], signal),
    enabled: scope.ready,
    staleTime: 30_000,
    retry: false,
  });
}
