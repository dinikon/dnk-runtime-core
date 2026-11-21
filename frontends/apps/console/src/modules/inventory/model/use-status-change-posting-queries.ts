import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import { statusChangePostingKeys } from "./status-change-posting.query-keys";
import {
  prepareStatusChange,
  listStatusChangeSources,
  listStatusChangeExecutions,
} from "../api/status-change-posting.api";
import type {
  StatusChangePreparation,
  StatusChangeSources,
  StatusChangeSourceParams,
  StatusChangeExecutionHistory,
} from "./status-change-posting.types";
export function useStatusChangePreparation(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<StatusChangePreparation, Error> {
  return useQuery({
    queryKey: computed(() =>
      statusChangePostingKeys.context(scope.key.value, id.value),
    ),
    queryFn: ({ queryKey, signal }) => prepareStatusChange(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
export function useStatusChangeSources(
  id: Ref<string>,
  params: Ref<StatusChangeSourceParams>,
  enabled: Ref<boolean>,
  scope: InventoryScopeState,
): UseQueryReturnType<StatusChangeSources, Error> {
  return useQuery({
    queryKey: computed(() =>
      statusChangePostingKeys.sources(scope.key.value, id.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listStatusChangeSources(queryKey[6], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && enabled.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
export function useStatusChangeExecutionHistory(
  id: Ref<string>,
  offset: Ref<number>,
  scope: InventoryScopeState,
): UseQueryReturnType<StatusChangeExecutionHistory, Error> {
  return useQuery({
    queryKey: computed(() =>
      statusChangePostingKeys.history(scope.key.value, id.value, offset.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listStatusChangeExecutions(queryKey[6], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}

import { useQueryClient } from "@tanstack/vue-query";
import type { InventoryScope } from "./inventory-scope.types";
import type {
  StatusChangeAllocation,
  StatusChangeSource,
} from "./status-change-posting.types";
interface StatusChangeSourceSnapshots {
  refresh: (
    id: string,
    rows: readonly StatusChangeAllocation[],
    captured: InventoryScope,
    signal: AbortSignal,
  ) => Promise<Map<string, StatusChangeSource | null>>;
}
export function useStatusChangeSourceSnapshots(): StatusChangeSourceSnapshots {
  const cache = useQueryClient();
  async function refresh(
    id: string,
    rows: readonly StatusChangeAllocation[],
    captured: InventoryScope,
    signal: AbortSignal,
  ): Promise<Map<string, StatusChangeSource | null>> {
    const unique = new Map(
      rows
        .filter((v) => v.selected && v.source)
        .map((v) => [JSON.stringify([v.documentLineId, v.source!.id]), v]),
    );
    const result = new Map<string, StatusChangeSource | null>();
    for (const [key, row] of unique) {
      const params: StatusChangeSourceParams = {
        documentLineId: row.documentLineId,
        positionId: row.source?.id,
        offset: 0,
        search: "",
      };
      const page = await cache.fetchQuery({
        queryKey: statusChangePostingKeys.sources(captured, id, params),
        queryFn: ({ signal: querySignal }) =>
          listStatusChangeSources(
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
