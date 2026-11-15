import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import { issuePostingKeys } from "./issue-posting.query-keys";
import {
  prepareIssue,
  listIssueSources,
  listIssueExecutions,
} from "../api/issue-posting.api";
import type {
  IssuePreparation,
  IssueSources,
  IssueSourceParams,
  IssueExecutionHistory,
} from "./issue-posting.types";
export function useIssuePreparation(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<IssuePreparation, Error> {
  return useQuery({
    queryKey: computed(() =>
      issuePostingKeys.context(scope.key.value, id.value),
    ),
    queryFn: ({ queryKey, signal }) => prepareIssue(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
export function useIssueSources(
  id: Ref<string>,
  params: Ref<IssueSourceParams>,
  enabled: Ref<boolean>,
  scope: InventoryScopeState,
): UseQueryReturnType<IssueSources, Error> {
  return useQuery({
    queryKey: computed(() =>
      issuePostingKeys.sources(scope.key.value, id.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listIssueSources(queryKey[6], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && enabled.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
export function useIssueExecutionHistory(
  id: Ref<string>,
  offset: Ref<number>,
  scope: InventoryScopeState,
): UseQueryReturnType<IssueExecutionHistory, Error> {
  return useQuery({
    queryKey: computed(() =>
      issuePostingKeys.history(scope.key.value, id.value, offset.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listIssueExecutions(queryKey[6], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}

import { useQueryClient } from "@tanstack/vue-query";
import type { InventoryScope } from "./inventory-scope.types";
import type { IssueAllocation, IssueSource } from "./issue-posting.types";
interface IssueSourceSnapshots {
  refresh: (
    id: string,
    rows: readonly IssueAllocation[],
    captured: InventoryScope,
    signal: AbortSignal,
  ) => Promise<Map<string, IssueSource | null>>;
}
export function useIssueSourceSnapshots(): IssueSourceSnapshots {
  const cache = useQueryClient();
  async function refresh(
    id: string,
    rows: readonly IssueAllocation[],
    captured: InventoryScope,
    signal: AbortSignal,
  ): Promise<Map<string, IssueSource | null>> {
    const unique = new Map(
      rows
        .filter((v) => v.selected && v.source)
        .map((v) => [JSON.stringify([v.documentLineId, v.source!.id]), v]),
    );
    const result = new Map<string, IssueSource | null>();
    for (const [key, row] of unique) {
      const params: IssueSourceParams = {
        documentLineId: row.documentLineId,
        positionId: row.source?.id,
        offset: 0,
        search: "",
      };
      const page = await cache.fetchQuery({
        queryKey: issuePostingKeys.sources(captured, id, params),
        queryFn: ({ signal: querySignal }) =>
          listIssueSources(id, params, AbortSignal.any([signal, querySignal])),
        staleTime: 0,
      });
      result.set(key, page.items[0] ?? null);
    }
    return result;
  }
  return { refresh };
}
