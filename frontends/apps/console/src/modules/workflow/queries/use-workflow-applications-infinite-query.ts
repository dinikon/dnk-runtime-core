import { computed, type Ref } from "vue";
import {
  type InfiniteData,
  type QueryFunctionContext,
  useInfiniteQuery,
} from "@tanstack/vue-query";

import { listWorkflowApplications } from "@/modules/workflow/api/workflow-application.api.ts";
import {
  type WorkflowApplicationsQueryKey,
  workflowQueryKeys,
} from "@/modules/workflow/queries/workflow.query-keys.ts";
import type {
  WorkflowApplicationListItem,
  WorkflowApplicationListResponse,
  WorkflowCursor,
} from "@/modules/workflow/model/workflow-application.types.ts";

export function useWorkflowApplicationsInfiniteQuery(limit: Ref<number>) {
  const queryKey = computed<WorkflowApplicationsQueryKey>(() =>
    workflowQueryKeys.applicationsList({
      limit: limit.value,
    }),
  );

  const query = useInfiniteQuery<
    WorkflowApplicationListResponse,
    Error,
    InfiniteData<WorkflowApplicationListResponse>,
    WorkflowApplicationsQueryKey,
    WorkflowCursor
  >({
    queryKey,

    initialPageParam: null,

    queryFn: (
      context: QueryFunctionContext<
        WorkflowApplicationsQueryKey,
        WorkflowCursor
      >,
    ) => {
      const [, , params] = context.queryKey;

      return listWorkflowApplications({
        limit: params.limit,
        cursor: context.pageParam,
      });
    },

    getNextPageParam: (lastPage) => {
      return lastPage.nextCursor ?? undefined;
    },
  });

  const items = computed<WorkflowApplicationListItem[]>(() => {
    return query.data.value?.pages.flatMap((page) => page.items) ?? [];
  });

  const pageCount = computed(() => {
    return query.data.value?.pages.length ?? 0;
  });

  const lastNextCursor = computed(() => {
    const pages = query.data.value?.pages ?? [];

    return pages.at(-1)?.nextCursor ?? null;
  });

  async function loadMore(): Promise<void> {
    if (!query.hasNextPage.value || query.isFetchingNextPage.value) {
      return;
    }

    await query.fetchNextPage();
  }

  return {
    data: query.data,
    error: query.error,

    isPending: query.isPending,
    isError: query.isError,
    isFetching: query.isFetching,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage,

    items,
    pageCount,
    lastNextCursor,

    loadMore,
  };
}
