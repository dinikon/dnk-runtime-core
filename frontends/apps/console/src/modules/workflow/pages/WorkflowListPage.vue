<script setup lang="ts">
import {computed, ref} from "vue";
import {type InfiniteData, type QueryFunctionContext, useInfiniteQuery,} from "@tanstack/vue-query";

import {httpClient} from "@/app/providers/http";
import {CursorPagination} from "@/shared/pagination";

/**
 * DTO — то, что приходит с API.
 */
interface WorkflowApplicationListItemDto {
  id: string;
  created_at: string;
  kind: string;
  status: string;
  title: string;
  description: string | null;
  icon: string;
  icon_background: string;
}

interface WorkflowApplicationListResponseDto {
  items: WorkflowApplicationListItemDto[];
  next_cursor: string | null;
}

/**
 * Frontend model — то, с чем удобнее работать в UI.
 */
interface WorkflowApplicationListItem {
  id: string;
  createdAt: string;
  kind: string;
  status: string;
  title: string;
  description: string | null;
  icon: string;
  iconBackground: string;
}

interface WorkflowApplicationListResponse {
  items: WorkflowApplicationListItem[];
  nextCursor: string | null;
}

type WorkflowCursor = string | null;

type WorkflowApplicationsQueryKey = readonly [
  "console-workflows",
  {
    readonly limit: number;
  },
];

function mapWorkflowApplicationListItem(
  dto: WorkflowApplicationListItemDto,
): WorkflowApplicationListItem {
  return {
    id: dto.id,
    createdAt: dto.created_at,
    kind: dto.kind,
    status: dto.status,
    title: dto.title,
    description: dto.description,
    icon: dto.icon,
    iconBackground: dto.icon_background,
  };
}

function mapWorkflowApplicationList(
  dto: WorkflowApplicationListResponseDto,
): WorkflowApplicationListResponse {
  return {
    items: dto.items.map(mapWorkflowApplicationListItem),
    nextCursor: dto.next_cursor,
  };
}

const limit = ref(1);

const queryKey = computed<WorkflowApplicationsQueryKey>(() => [
  "console-workflows",
  {
    limit: limit.value,
  },
]);

async function fetchWorkflowApplications(
  context: QueryFunctionContext<WorkflowApplicationsQueryKey, WorkflowCursor>,
): Promise<WorkflowApplicationListResponse> {
  const [, params] = context.queryKey;
  const cursor = context.pageParam;

  try {
    const response = await httpClient.get<WorkflowApplicationListResponseDto>(
      "/console/workflows",
      {
        params: {
          limit: params.limit,

          /**
           * Для первого запроса cursor === null.
           * В таком случае cursor лучше не отправлять вообще.
           *
           * Первый запрос:
           * GET /console/workflows?limit=20
           *
           * Следующий запрос:
           * GET /console/workflows?limit=20&cursor=abc123
           */
          cursor: cursor ?? undefined,
        },
      },
    );

    return mapWorkflowApplicationList(response.data);
  } catch (error) {
    console.error("[Workflow API] Fetch failed:", error);

    throw error;
  }
}

const {
  data,
  error,
  fetchNextPage,
  hasNextPage,
  isFetching,
  isFetchingNextPage,
  isPending,
  isError,
} = useInfiniteQuery<
  WorkflowApplicationListResponse,
  Error,
  InfiniteData<WorkflowApplicationListResponse>,
  WorkflowApplicationsQueryKey,
  WorkflowCursor
>({
  queryKey,

  queryFn: fetchWorkflowApplications,

  /**
   * Первый запрос будет без cursor.
   */
  initialPageParam: null,

  /**
   * lastPage — последняя загруженная страница.
   *
   * Если API вернул nextCursor, TanStack передаст его
   * в следующий вызов queryFn как context.pageParam.
   *
   * Если вернуть undefined — следующей страницы нет.
   */
  getNextPageParam: (lastPage) => {

    return lastPage.nextCursor ?? undefined;
  },
});

const items = computed<WorkflowApplicationListItem[]>(() => {
  return data.value?.pages.flatMap((page) => page.items) ?? [];
});

const pageCount = computed(() => {
  return data.value?.pages.length ?? 0;
});

const lastNextCursor = computed(() => {
  const pages = data.value?.pages ?? [];

  return pages.at(-1)?.nextCursor ?? null;
});


function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

async function handleLoadMore(): Promise<void> {
  if (!hasNextPage.value || isFetchingNextPage.value) {
    return;
  }

  await fetchNextPage();
}
</script>

<template>
  <section class="workflow-test-stand">
    <header class="workflow-test-stand__header">
      <div>
        <h1>Workflow Infinite Query Test Stand</h1>

        <p>
          GET /console/workflows?limit={{ limit }}
          <template v-if="lastNextCursor">
            &cursor={{ lastNextCursor }}
          </template>
        </p>
      </div>

      <div class="workflow-test-stand__actions">
        <label>
          Limit:

          <select v-model.number="limit">
            <option :value="1">1</option>
          </select>
        </label>

      </div>
    </header>

    <div v-if="isPending" class="workflow-test-stand__state">
      Loading first page...
    </div>

    <div v-else-if="isError" class="workflow-test-stand__error">
      Error: {{ error?.message }}
    </div>

    <template v-else>
      <div class="workflow-test-stand__summary">
        <span>Pages: {{ pageCount }}</span>
        <span>Items: {{ items.length }}</span>
        <span>Has next page: {{ hasNextPage ? "yes" : "no" }}</span>
        <span>Last cursor: {{ lastNextCursor ?? "—" }}</span>
      </div>

      <div
        v-if="isFetching && !isFetchingNextPage"
        class="workflow-test-stand__scroll"
      >
        Background fetching...
      </div>

      <ul class="workflow-test-stand__list">
        <li
          v-for="workflow in items"
          :key="workflow.id"
          class="workflow-test-stand__item"
        >
          <div
            class="workflow-test-stand__icon"
            :style="{ background: workflow.iconBackground }"
          >
            {{ workflow.icon }}
          </div>

          <div class="workflow-test-stand__content">
            <strong>{{ workflow.title }}</strong>

            <p v-if="workflow.description">
              {{ workflow.description }}
            </p>

            <div class="workflow-test-stand__meta">
              <span>ID: {{ workflow.id }}</span>
              <span>Kind: {{ workflow.kind }}</span>
              <span>Status: {{ workflow.status }}</span>
              <span>Created: {{ formatDate(workflow.createdAt) }}</span>
            </div>
          </div>
        </li>
      </ul>

      <button
      @click="() => fetchNextPage()"
      :disabled="!hasNextPage || isFetchingNextPage"
    >
      <span v-if="isFetchingNextPage">Loading more...</span>
      <span v-else-if="hasNextPage">Load More</span>
      <span v-else>Nothing more to load</span>
    </button>
      <CursorPagination
        :has-more="hasNextPage"
        :loading="isFetchingNextPage"
        :disabled="isFetching && !isFetchingNextPage"
        mode="infinite"
        loading-text="Loading more..."
        load-more-text="Load more"
        end-text="Nothing more to load"
        @load-more="handleLoadMore"
      />
    </template>
  </section>
</template>