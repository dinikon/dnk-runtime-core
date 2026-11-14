import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { useScopedQueryCache } from "@/shared/model/use-scoped-query-cache";
import { searchCounterpartyReferences } from "../api/counterparty-reference.api";
import type {
  CounterpartyReferenceScope,
  CounterpartyReferencesParams,
  CounterpartyReferencesPage,
} from "./counterparty-reference.types";
import { counterpartyReferenceKeys } from "./counterparty-reference.query-keys";
export function useCounterpartyReferencesQuery(
  params: Ref<CounterpartyReferencesParams>,
  scope: Ref<CounterpartyReferenceScope>,
  enabled: Ref<boolean>,
): UseQueryReturnType<CounterpartyReferencesPage, Error> {
  useScopedQueryCache(scope, "crm-counterparty-references");
  return useQuery({
    queryKey: computed(() =>
      counterpartyReferenceKeys.list(scope.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      searchCounterpartyReferences(queryKey[4], signal),
    enabled,
    staleTime: 30_000,
    retry: false,
  });
}
