import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import { returnPostingKeys } from "./return-posting.query-keys";
import {
  prepareReturn,
  listReturnSources,
  listReturnExecutions,
} from "../api/return-posting.api";
import type {
  ReturnPreparation,
  ReturnSources,
  ReturnSourceParams,
  ReturnExecutionHistory,
} from "./return-posting.types";
export function useReturnPreparation(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReturnPreparation, Error> {
  return useQuery({
    queryKey: computed(() =>
      returnPostingKeys.context(scope.key.value, id.value),
    ),
    queryFn: ({ queryKey, signal }) => prepareReturn(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
export function useReturnSources(
  id: Ref<string>,
  params: Ref<ReturnSourceParams>,
  enabled: Ref<boolean>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReturnSources, Error> {
  return useQuery({
    queryKey: computed(() =>
      returnPostingKeys.sources(scope.key.value, id.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listReturnSources(queryKey[6], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && enabled.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
export function useReturnExecutionHistory(
  id: Ref<string>,
  offset: Ref<number>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReturnExecutionHistory, Error> {
  return useQuery({
    queryKey: computed(() =>
      returnPostingKeys.history(scope.key.value, id.value, offset.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listReturnExecutions(queryKey[6], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}

import { useQueryClient } from "@tanstack/vue-query";
import type { InventoryScope } from "./inventory-scope.types";
import type { ReturnAllocation, ReturnSource } from "./return-posting.types";
interface ReturnSourceSnapshots {
  refresh: (
    id: string,
    rows: readonly ReturnAllocation[],
    captured: InventoryScope,
    signal: AbortSignal,
  ) => Promise<Map<string, ReturnSource | null>>;
}
export function useReturnSourceSnapshots(): ReturnSourceSnapshots {
  const cache = useQueryClient();
  async function refresh(
    id: string,
    rows: readonly ReturnAllocation[],
    captured: InventoryScope,
    signal: AbortSignal,
  ): Promise<Map<string, ReturnSource | null>> {
    const unique = new Map(
      rows
        .filter((v) => v.selected && v.source)
        .map((v) => [JSON.stringify([v.documentLineId, v.source!.id]), v]),
    );
    const result = new Map<string, ReturnSource | null>();
    for (const [key, row] of unique) {
      const params: ReturnSourceParams = {
        documentLineId: row.documentLineId,
        positionId: row.source?.id,
        offset: 0,
        search: "",
      };
      const page = await cache.fetchQuery({
        queryKey: returnPostingKeys.sources(captured, id, params),
        queryFn: ({ signal: querySignal }) =>
          listReturnSources(id, params, AbortSignal.any([signal, querySignal])),
        staleTime: 0,
      });
      result.set(key, page.items[0] ?? null);
    }
    return result;
  }
  return { refresh };
}

import { listReturnDestinations } from "../api/return-posting.api";
import type {
  ReturnDestinations,
  ReturnDestinationParams,
} from "./return-posting.types";
export function useReturnDestinations(
  id: Ref<string>,
  params: Ref<ReturnDestinationParams>,
  enabled: Ref<boolean>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReturnDestinations, Error> {
  return useQuery({
    queryKey: computed(() =>
      returnPostingKeys.destinations(scope.key.value, id.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listReturnDestinations(queryKey[6], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && !!id.value && enabled.value),
    staleTime: 0,
    retry: false,
  });
}
