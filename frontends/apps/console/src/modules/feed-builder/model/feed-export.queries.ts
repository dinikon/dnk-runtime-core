import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { feedExportApi } from "../api/feed-export.api";
import { feedKeys, type FeedScope } from "./feed.query-keys";
import { useFeedScope } from "./use-feed-scope";
import type {
  ExportIssueSeverity,
  FeedExportIssues,
  FeedExportState,
} from "./feed-export.types";

export const exportKeys = {
  state: (scope: FeedScope, id: string) =>
    [...feedKeys.root(scope), "export-state", id] as const,
  issues: (
    scope: FeedScope,
    id: string,
    completedAt: string | undefined,
    severity: ExportIssueSeverity | "",
    offset: number,
  ) =>
    [
      ...feedKeys.root(scope),
      "export-issues",
      id,
      completedAt,
      severity,
      offset,
    ] as const,
};

export function useFeedExport(
  id: Ref<string>,
): UseQueryReturnType<FeedExportState, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() => exportKeys.state(scope.value, id.value)),
    queryFn: ({ queryKey, signal }) => feedExportApi.get(queryKey[5], signal),
    enabled: computed(() =>
      Boolean(scope.value[0] && scope.value[1] && id.value),
    ),
    refetchInterval: (query) => (query.state.data?.task ? 1000 : false),
    retry: false,
  });
}

export function useLatestFeedExportIssues(
  id: Ref<string>,
  completedAt: Ref<string | undefined>,
  severity: Ref<ExportIssueSeverity | "">,
  offset: Ref<number>,
): UseQueryReturnType<FeedExportIssues, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() =>
      exportKeys.issues(
        scope.value,
        id.value,
        completedAt.value,
        severity.value,
        offset.value,
      ),
    ),
    queryFn: ({ queryKey, signal }) =>
      feedExportApi.listIssues(queryKey[5], queryKey[7], queryKey[8], signal),
    enabled: computed(() =>
      Boolean(
        scope.value[0] && scope.value[1] && id.value && completedAt.value,
      ),
    ),
    retry: false,
  });
}
