import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type {
  InternalMovesPage,
  InternalMovesParams,
} from "./internal-move.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { internalMoveKeys } from "./internal-move.query-keys";
import { listInternalMoves } from "../api/internal-move.api";
export function useInternalMovesQuery(
  params: Ref<InternalMovesParams>,
  scope: InventoryScopeState,
): UseQueryReturnType<InternalMovesPage, Error> {
  return useQuery({
    queryKey: computed(() =>
      internalMoveKeys.list(scope.key.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) => listInternalMoves(queryKey[6], signal),
    enabled: scope.ready,
    staleTime: 30_000,
    retry: false,
  });
}
