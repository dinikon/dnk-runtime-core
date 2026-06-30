import { computed, type Ref } from "vue";
import {
  type InfiniteData,
  type QueryFunctionContext,
  useInfiniteQuery,
} from "@tanstack/vue-query";

import type { WorkflowApplicationListResponseDto } from "@/modules/workflow/applications/api/workflow-application.dto.ts";
import { listWorkflowApplications } from "@/modules/workflow/applications/api/workflow-application.api.ts";
import { mapWorkflowApplicationList } from "@/modules/workflow/applications/model/workflow-application.mapper.ts";
import {
  type WorkflowApplicationsQueryKey,
  workflowApplicationQueryKeys,
} from "@/modules/workflow/applications/model/workflow-application.query-keys.ts";
import type {
  WorkflowApplicationListItem,
  WorkflowCursor,
} from "@/modules/workflow/applications/model/workflow-application.types.ts";

export function useWorkflowApplicationsQuery(limit: Ref<number>) {
  const queryKey = computed<WorkflowApplicationsQueryKey>(() =>
    workflowApplicationQueryKeys.applicationsList({
      limit: limit.value,
    }),
  );

  const query = useInfiniteQuery<
    WorkflowApplicationListResponseDto,
    Error,
    InfiniteData<WorkflowApplicationListResponseDto>,
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
      return lastPage.next_cursor ?? undefined;
    },
  });

  const items = computed<WorkflowApplicationListItem[]>(() => {
    return (
      query.data.value?.pages.flatMap((page) => {
        return mapWorkflowApplicationList(page).items;
      }) ?? []
    );
  });

  const pageCount = computed(() => {
    return query.data.value?.pages.length ?? 0;
  });

  const lastNextCursor = computed(() => {
    const pages = query.data.value?.pages ?? [];

    return pages.at(-1)?.next_cursor ?? null;
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
