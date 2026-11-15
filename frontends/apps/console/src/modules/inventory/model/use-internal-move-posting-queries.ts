import type {
  InternalMoveDestinationParams,
  InternalMoveDestinations,
  InternalMoveDestination,
} from "./internal-move-posting.types";
import { listInternalMoveDestinations } from "../api/internal-move-posting.api";
import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import { internalMovePostingKeys } from "./internal-move-posting.query-keys";
import {
  prepareInternalMove,
  listInternalMoveSources,
  listInternalMoveExecutions,
} from "../api/internal-move-posting.api";
import type {
  InternalMovePreparation,
  InternalMoveSources,
  InternalMoveSourceParams,
  InternalMoveExecutionHistory,
} from "./internal-move-posting.types";
export function useInternalMovePreparation(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<InternalMovePreparation, Error> {
  return useQuery({
    queryKey: computed(() =>
      internalMovePostingKeys.context(scope.key.value, id.value),
    ),
    queryFn: ({ queryKey, signal }) => prepareInternalMove(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
export function useInternalMoveSources(
  id: Ref<string>,
  params: Ref<InternalMoveSourceParams>,
  enabled: Ref<boolean>,
  scope: InventoryScopeState,
): UseQueryReturnType<InternalMoveSources, Error> {
  return useQuery({
    queryKey: computed(() =>
      internalMovePostingKeys.sources(scope.key.value, id.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listInternalMoveSources(queryKey[6], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && enabled.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
export function useInternalMoveExecutionHistory(
  id: Ref<string>,
  offset: Ref<number>,
  scope: InventoryScopeState,
): UseQueryReturnType<InternalMoveExecutionHistory, Error> {
  return useQuery({
    queryKey: computed(() =>
      internalMovePostingKeys.history(scope.key.value, id.value, offset.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listInternalMoveExecutions(queryKey[6], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}

import { useQueryClient } from "@tanstack/vue-query";
import type { InventoryScope } from "./inventory-scope.types";
import type {
  InternalMoveAllocation,
  InternalMoveSource,
} from "./internal-move-posting.types";
interface InternalMoveSourceSnapshots {
  refresh: (
    id: string,
    rows: readonly InternalMoveAllocation[],
    captured: InventoryScope,
    signal: AbortSignal,
  ) => Promise<Map<string, InternalMoveSource | null>>;
}
export function useInternalMoveSourceSnapshots(): InternalMoveSourceSnapshots {
  const cache = useQueryClient();
  async function refresh(
    id: string,
    rows: readonly InternalMoveAllocation[],
    captured: InventoryScope,
    signal: AbortSignal,
  ): Promise<Map<string, InternalMoveSource | null>> {
    const unique = new Map(
      rows
        .filter((v) => v.selected && v.source)
        .map((v) => [JSON.stringify([v.documentLineId, v.source!.id]), v]),
    );
    const result = new Map<string, InternalMoveSource | null>();
    for (const [key, row] of unique) {
      const params: InternalMoveSourceParams = {
        documentLineId: row.documentLineId,
        positionId: row.source?.id,
        offset: 0,
        search: "",
      };
      const page = await cache.fetchQuery({
        queryKey: internalMovePostingKeys.sources(captured, id, params),
        queryFn: ({ signal: querySignal }) =>
          listInternalMoveSources(
            id,
            params,
            AbortSignal.any([signal, querySignal]),
          ),
        staleTime: 0,
      });
      result.set(key, page.items[0] ?? null);
    }
    return result;
  }
  return { refresh };
}

export function useInternalMoveDestinations(
  id: Ref<string>,
  params: Ref<InternalMoveDestinationParams>,
  enabled: Ref<boolean>,
  scope: InventoryScopeState,
): UseQueryReturnType<InternalMoveDestinations, Error> {
  return useQuery({
    queryKey: computed(() =>
      internalMovePostingKeys.destinations(
        scope.key.value,
        id.value,
        params.value,
      ),
    ),
    queryFn: ({ queryKey, signal }) =>
      listInternalMoveDestinations(queryKey[6], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && enabled.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
interface InternalMoveDestinationSnapshots {
  refresh: (
    id: string,
    rows: readonly InternalMoveAllocation[],
    captured: InventoryScope,
    signal: AbortSignal,
  ) => Promise<Map<string, InternalMoveDestination | null>>;
}
export function useInternalMoveDestinationSnapshots(): InternalMoveDestinationSnapshots {
  const cache = useQueryClient();
  async function refresh(
    id: string,
    rows: readonly InternalMoveAllocation[],
    captured: InventoryScope,
    signal: AbortSignal,
  ): Promise<Map<string, InternalMoveDestination | null>> {
    const result = new Map<string, InternalMoveDestination | null>();
    for (const locationId of new Set(
      rows
        .filter((v) => v.selected && v.destination)
        .map((v) => v.destination!.id),
    )) {
      const params: InternalMoveDestinationParams = {
        locationId,
        offset: 0,
        search: "",
      };
      const page = await cache.fetchQuery({
        queryKey: internalMovePostingKeys.destinations(captured, id, params),
        queryFn: ({ signal: querySignal }) =>
          listInternalMoveDestinations(
            id,
            params,
            AbortSignal.any([signal, querySignal]),
          ),
        staleTime: 0,
      });
      result.set(locationId, page.items[0] ?? null);
    }
    return result;
  }
  return { refresh };
}
