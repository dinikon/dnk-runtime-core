import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import { writeOffPostingKeys } from "./write-off-posting.query-keys";
import {
  prepareWriteOff,
  listWriteOffSources,
  listWriteOffExecutions,
} from "../api/write-off-posting.api";
import type {
  WriteOffPreparation,
  WriteOffSources,
  WriteOffSourceParams,
  WriteOffExecutionHistory,
} from "./write-off-posting.types";
export function useWriteOffPreparation(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<WriteOffPreparation, Error> {
  return useQuery({
    queryKey: computed(() =>
      writeOffPostingKeys.context(scope.key.value, id.value),
    ),
    queryFn: ({ queryKey, signal }) => prepareWriteOff(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
export function useWriteOffSources(
  id: Ref<string>,
  params: Ref<WriteOffSourceParams>,
  enabled: Ref<boolean>,
  scope: InventoryScopeState,
): UseQueryReturnType<WriteOffSources, Error> {
  return useQuery({
    queryKey: computed(() =>
      writeOffPostingKeys.sources(scope.key.value, id.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listWriteOffSources(queryKey[6], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && enabled.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
export function useWriteOffExecutionHistory(
  id: Ref<string>,
  offset: Ref<number>,
  scope: InventoryScopeState,
): UseQueryReturnType<WriteOffExecutionHistory, Error> {
  return useQuery({
    queryKey: computed(() =>
      writeOffPostingKeys.history(scope.key.value, id.value, offset.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listWriteOffExecutions(queryKey[6], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}

import { useQueryClient } from "@tanstack/vue-query";
import type { InventoryScope } from "./inventory-scope.types";
import type {
  WriteOffAllocation,
  WriteOffSource,
} from "./write-off-posting.types";
interface WriteOffSourceSnapshots {
  refresh: (
    id: string,
    rows: readonly WriteOffAllocation[],
    captured: InventoryScope,
    signal: AbortSignal,
  ) => Promise<Map<string, WriteOffSource | null>>;
}
export function useWriteOffSourceSnapshots(): WriteOffSourceSnapshots {
  const cache = useQueryClient();
  async function refresh(
    id: string,
    rows: readonly WriteOffAllocation[],
    captured: InventoryScope,
    signal: AbortSignal,
  ): Promise<Map<string, WriteOffSource | null>> {
    const unique = new Map(
      rows
        .filter((v) => v.selected && v.source)
        .map((v) => [JSON.stringify([v.documentLineId, v.source!.id]), v]),
    );
    const result = new Map<string, WriteOffSource | null>();
    for (const [key, row] of unique) {
      const params: WriteOffSourceParams = {
        documentLineId: row.documentLineId,
        positionId: row.source?.id,
        offset: 0,
        search: "",
      };
      const page = await cache.fetchQuery({
        queryKey: writeOffPostingKeys.sources(captured, id, params),
        queryFn: ({ signal: querySignal }) =>
          listWriteOffSources(
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
