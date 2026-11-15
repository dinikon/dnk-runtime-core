import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { WriteOffsPage, WriteOffsParams } from "./write-off.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { writeOffKeys } from "./write-off.query-keys";
import { listWriteOffs } from "../api/write-off.api";
export function useWriteOffsQuery(
  params: Ref<WriteOffsParams>,
  scope: InventoryScopeState,
): UseQueryReturnType<WriteOffsPage, Error> {
  return useQuery({
    queryKey: computed(() => writeOffKeys.list(scope.key.value, params.value)),
    queryFn: ({ queryKey, signal }) => listWriteOffs(queryKey[6], signal),
    enabled: scope.ready,
    staleTime: 30_000,
    retry: false,
  });
}
