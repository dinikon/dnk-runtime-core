import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type {
  StatusChangesPage,
  StatusChangesParams,
} from "./status-change.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { statusChangeKeys } from "./status-change.query-keys";
import { listStatusChanges } from "../api/status-change.api";
export function useStatusChangesQuery(
  params: Ref<StatusChangesParams>,
  scope: InventoryScopeState,
): UseQueryReturnType<StatusChangesPage, Error> {
  return useQuery({
    queryKey: computed(() =>
      statusChangeKeys.list(scope.key.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) => listStatusChanges(queryKey[6], signal),
    enabled: scope.ready,
    staleTime: 30_000,
    retry: false,
  });
}
