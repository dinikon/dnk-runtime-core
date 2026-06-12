<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Filter, Plus, RefreshCcw, Search, X } from "lucide-vue-next";
import { useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { useRoute, useRouter } from "vue-router";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  BroadcastListItem,
  CreateBroadcastPayload,
  ListBroadcastsPayload,
} from "@/modules/broadcast/api";
import BroadcastsTable from "@/modules/broadcast/components/BroadcastsTable.vue";
import CreateBroadcastDrawer from "@/modules/broadcast/components/CreateBroadcastDrawer.vue";
import { broadcastQueryKeys } from "@/modules/broadcast/model/broadcast.query-keys";
import { useCreateBroadcastMutation } from "@/modules/broadcast/mutations/use-create-broadcast-mutation";
import { useBroadcastFieldsQuery } from "@/modules/broadcast/queries/use-broadcast-fields-query";
import { useBroadcastsListQuery } from "@/modules/broadcast/queries/use-broadcasts-list-query";
import { apiErrorMessage } from "@/modules/broadcast/util";
import {
  areRuntimeFiltersEqual,
  areRuntimeSortsEqual,
  RUNTIME_OBJECT_PAGE_SIZES,
  sanitizeRuntimeFilterForFields,
  sanitizeRuntimeSortForFields,
  useRuntimeObjectQueryState,
} from "@/shared/runtime-object/composables/use-runtime-object-query-state";
import RuntimeObjectFilterBuilder from "@/shared/runtime-object/filters/RuntimeObjectFilterBuilder.vue";
import type {
  RuntimeFieldDescription,
  RuntimeFilter,
  RuntimeFilterCondition,
  RuntimeSort,
} from "@/shared/runtime-object";

const queryClient = useQueryClient();
const route = useRoute();
const router = useRouter();
const queryState = useRuntimeObjectQueryState();

const filterSheetOpen = ref(false);
const createDrawerOpen = ref(false);
const createError = ref<string | null>(null);
const searchDraft = ref("");
const appliedSearch = ref("");

const fieldsQuery = useBroadcastFieldsQuery();
const schema = computed(() => fieldsQuery.data.value);
const fields = computed(() => schema.value?.fields ?? []);
const searchField = computed(() => findSearchField(fields.value));
const canSearch = computed(() => !!searchField.value);
const advancedFilter = computed(() =>
  sanitizeRuntimeFilterForFields(queryState.filter.value, fields.value),
);
const searchFilter = computed(() => createSearchFilter(appliedSearch.value));
const filter = computed(() =>
  mergeFilters(advancedFilter.value, searchFilter.value),
);
const sort = computed(() =>
  sanitizeRuntimeSortForFields(queryState.sort.value, fields.value),
);
const limit = queryState.limit;
const offset = queryState.offset;
const listEnabled = computed(() => !!schema.value);

const listPayload = computed<ListBroadcastsPayload>(() => ({
  filter: filter.value,
  sort: sort.value,
  pagination: {
    limit: limit.value,
    offset: offset.value,
  },
}));

const listQuery = useBroadcastsListQuery(listPayload, listEnabled);
const createMutation = useCreateBroadcastMutation();

const records = computed<BroadcastListItem[]>(
  () => listQuery.data.value?.data ?? [],
);
const pagination = computed(() => listQuery.data.value?.pagination);
const total = computed(() => pagination.value?.total ?? 0);
const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1);
const pageStart = computed(() => (total.value === 0 ? 0 : offset.value + 1));
const pageEnd = computed(() =>
  Math.min(offset.value + limit.value, total.value),
);
const canGoPrevious = computed(() => offset.value > 0);
const canGoNext = computed(() => offset.value + limit.value < total.value);
const isInitialTableLoading = computed(
  () =>
    fieldsQuery.isLoading.value ||
    (listQuery.isLoading.value && records.value.length === 0),
);
const isTableRefreshing = computed(
  () => !isInitialTableLoading.value && listQuery.isFetching.value,
);
const filterCount = computed(() => countFilterConditions(filter.value));
const hasFilterableFields = computed(() =>
  fields.value.some((field) => field.filter.enabled),
);
const pageTitle = computed(
  () => schema.value?.object.plural_label ?? "Broadcasts",
);
const pageDescription = computed(
  () =>
    schema.value?.object.description ??
    "Server-side broadcast list with runtime filters and sorting.",
);

watch(
  [fields, queryState.filter, queryState.sort, queryState.hasInvalidQuery],
  () => {
    if (!schema.value) {
      return;
    }

    if (
      queryState.hasInvalidQuery.value ||
      !areRuntimeFiltersEqual(advancedFilter.value, queryState.filter.value) ||
      !areRuntimeSortsEqual(sort.value, queryState.sort.value)
    ) {
      void queryState.replaceState({
        filter: advancedFilter.value,
        sort: sort.value,
        limit: limit.value,
        offset: offset.value,
      });
    }
  },
  { immediate: true },
);

watch(pagination, (nextPagination) => {
  if (!nextPagination) {
    return;
  }

  const lastOffset =
    nextPagination.total === 0
      ? 0
      : Math.floor((nextPagination.total - 1) / limit.value) * limit.value;

  if (offset.value > lastOffset) {
    void queryState.replaceState({ offset: lastOffset });
  }
});

function createSearchFilter(value: string): RuntimeFilterCondition | null {
  const trimmed = value.trim();
  const field = searchField.value;

  if (!trimmed || !field) {
    return null;
  }

  return {
    field: field.field_name,
    op: searchOperator(field),
    value: trimmed,
  };
}

function findSearchField(
  availableFields: RuntimeFieldDescription[],
): RuntimeFieldDescription | null {
  const preferredFields = ["title", "description"];

  for (const fieldName of preferredFields) {
    const field = availableFields.find(
      (item) => item.field_name === fieldName && isSearchableField(item),
    );

    if (field) {
      return field;
    }
  }

  return availableFields.find((field) => isSearchableField(field)) ?? null;
}

function isSearchableField(field: RuntimeFieldDescription): boolean {
  return field.filter.enabled && searchOperatorOrNull(field) !== null;
}

function searchOperator(field: RuntimeFieldDescription): string {
  return searchOperatorOrNull(field) ?? field.filter.operators[0];
}

function searchOperatorOrNull(field: RuntimeFieldDescription): string | null {
  const operators = field.filter.operators;
  return (
    ["contains", "icontains", "like", "ilike", "eq"].find((operator) =>
      operators.includes(operator),
    ) ?? null
  );
}

function mergeFilters(
  left: RuntimeFilter | null,
  right: RuntimeFilter | null,
): RuntimeFilter | null {
  if (!left) {
    return right;
  }

  if (!right) {
    return left;
  }

  return { and: [left, right] };
}

function countFilterConditions(value: RuntimeFilter | null): number {
  if (!value) {
    return 0;
  }

  if ("field" in value) {
    return 1;
  }

  if ("and" in value) {
    return value.and.reduce(
      (total, item) => total + countFilterConditions(item),
      0,
    );
  }

  return value.or.reduce(
    (total, item) => total + countFilterConditions(item),
    0,
  );
}

function applySearch() {
  const nextSearch = searchDraft.value.trim();

  if (nextSearch === appliedSearch.value) {
    return;
  }

  appliedSearch.value = nextSearch;
  void queryState.pushState({ offset: 0 });
}

function clearSearch() {
  searchDraft.value = "";
  appliedSearch.value = "";
  void queryState.pushState({ offset: 0 });
}

function applyFilter(nextFilter: RuntimeFilter | null) {
  filterSheetOpen.value = false;
  void queryState.pushState({ filter: nextFilter, offset: 0 });
}

function resetFilters() {
  searchDraft.value = "";
  appliedSearch.value = "";
  void queryState.pushState({ filter: null, offset: 0 });
}

function handleSortChange(nextSort: RuntimeSort[]) {
  void queryState.pushState({
    sort: sanitizeRuntimeSortForFields(nextSort, fields.value),
    offset: 0,
  });
}

function setPageSize(value: unknown) {
  const nextLimit = Number(value);

  if (!RUNTIME_OBJECT_PAGE_SIZES.some((pageSize) => pageSize === nextLimit)) {
    return;
  }

  void queryState.pushState({ limit: nextLimit, offset: 0 });
}

function goPrevious() {
  if (!canGoPrevious.value) {
    return;
  }

  void queryState.pushState({
    offset: Math.max(0, offset.value - limit.value),
  });
}

function goNext() {
  if (!canGoNext.value) {
    return;
  }

  void queryState.pushState({ offset: offset.value + limit.value });
}

function setPage(page: number) {
  void queryState.pushState({
    offset: Math.max(0, (page - 1) * limit.value),
  });
}

function openCreateDrawer() {
  createError.value = null;
  createDrawerOpen.value = true;
}

async function createBroadcast(payload: CreateBroadcastPayload) {
  createError.value = null;

  try {
    const broadcast = await createMutation.mutateAsync(payload);
    toast.success(`${broadcast.title} created.`);
    createDrawerOpen.value = false;

    if (offset.value !== 0) {
      await queryState.pushState({ offset: 0 });
    }

    await queryClient.invalidateQueries({
      queryKey: broadcastQueryKeys.lists(),
    });
  } catch (error) {
    createError.value = apiErrorMessage(error);
  }
}

function openBroadcast(record: BroadcastListItem) {
  void router.push({
    name: "broadcast-detail",
    params: { id: record.id },
    query: route.query,
  });
}
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
    <div
      class="flex shrink-0 flex-col gap-3 md:flex-row md:items-start md:justify-between"
    >
      <div class="grid gap-1">
        <h2 class="text-lg font-semibold tracking-normal">{{ pageTitle }}</h2>
        <p class="max-w-2xl text-sm text-muted-foreground">
          {{ pageDescription }}
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          :disabled="listQuery.isFetching.value"
          @click="listQuery.refetch()"
        >
          <RefreshCcw
            class="size-4"
            :class="{ 'animate-spin': listQuery.isFetching.value }"
          />
          Refresh
        </Button>
        <Button type="button" :disabled="!schema" @click="openCreateDrawer">
          <Plus class="size-4" />
          New broadcast
        </Button>
      </div>
    </div>

    <Alert v-if="fieldsQuery.error.value" variant="destructive">
      <AlertDescription>
        {{ apiErrorMessage(fieldsQuery.error.value) }}
      </AlertDescription>
    </Alert>
    <Alert v-if="listQuery.error.value" variant="destructive">
      <AlertDescription>
        {{ apiErrorMessage(listQuery.error.value) }}
      </AlertDescription>
    </Alert>

    <div
      class="flex shrink-0 flex-col gap-2 rounded-lg border bg-background p-3 md:flex-row md:items-center md:justify-between"
    >
      <form class="flex min-w-0 flex-1 gap-2" @submit.prevent="applySearch">
        <div class="relative min-w-0 flex-1 md:max-w-md">
          <Search
            class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            v-model="searchDraft"
            class="pl-9"
            :disabled="!canSearch"
            :placeholder="
              canSearch
                ? `Search by ${searchField?.label.toLowerCase()}`
                : 'Search is unavailable'
            "
          />
        </div>
        <Button type="submit" variant="outline" :disabled="!canSearch">
          Search
        </Button>
        <Button
          v-if="appliedSearch"
          type="button"
          variant="ghost"
          size="icon"
          aria-label="Clear search"
          @click="clearSearch"
        >
          <X class="size-4" />
        </Button>
      </form>

      <div class="flex flex-wrap gap-2">
        <Button
          v-if="hasFilterableFields"
          type="button"
          variant="outline"
          :disabled="!schema"
          @click="filterSheetOpen = true"
        >
          <Filter class="size-4" />
          Filters
          <span v-if="filterCount">({{ filterCount }})</span>
        </Button>
        <Button
          v-if="filterCount > 0"
          type="button"
          variant="outline"
          @click="resetFilters"
        >
          <X class="size-4" />
          Reset
        </Button>
      </div>
    </div>

    <BroadcastsTable
      v-if="schema"
      class="flex-1"
      :fields="fields"
      :records="records"
      :sort="sort"
      :is-loading="isInitialTableLoading"
      :is-refreshing="isTableRefreshing"
      @open="openBroadcast"
      @sort-change="handleSortChange"
    />

    <div v-else class="min-h-0 flex-1 rounded-lg border p-4">
      <div class="space-y-3">
        <Skeleton class="h-5 w-40" />
        <Skeleton class="h-10 w-full" />
        <Skeleton class="h-10 w-full" />
        <Skeleton class="h-10 w-full" />
      </div>
    </div>

    <div
      v-if="schema"
      class="flex shrink-0 flex-col gap-3 md:flex-row md:items-center md:justify-between"
    >
      <div class="flex flex-wrap items-center gap-3">
        <p class="text-sm text-muted-foreground">
          Showing {{ pageStart }}-{{ pageEnd }} of {{ total }}
        </p>
        <div class="flex items-center gap-2">
          <span class="text-sm text-muted-foreground">Rows per page</span>
          <Select
            :model-value="String(limit)"
            @update:model-value="setPageSize"
          >
            <SelectTrigger class="h-8 w-20">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="pageSize in RUNTIME_OBJECT_PAGE_SIZES"
                :key="pageSize"
                :value="String(pageSize)"
              >
                {{ pageSize }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <Pagination
        class="mx-0 justify-end"
        :items-per-page="limit"
        :page="currentPage"
        :total="total"
        @update:page="setPage"
      >
        <div class="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="!canGoPrevious || listQuery.isFetching.value"
            @click="goPrevious"
          >
            Previous
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="!canGoNext || listQuery.isFetching.value"
            @click="goNext"
          >
            Next
          </Button>
        </div>
      </Pagination>
    </div>

    <Sheet v-if="hasFilterableFields" v-model:open="filterSheetOpen">
      <SheetContent
        class="w-[min(34rem,100vw)] overflow-y-auto p-4 sm:max-w-xl"
      >
        <SheetHeader class="gap-1 p-0 pr-8">
          <SheetTitle>Filters</SheetTitle>
          <SheetDescription>
            Build a server-side filter from broadcast field metadata.
          </SheetDescription>
        </SheetHeader>
        <RuntimeObjectFilterBuilder
          class="mt-4"
          :fields="fields"
          :model-value="advancedFilter"
          @apply="applyFilter"
          @cancel="filterSheetOpen = false"
        />
      </SheetContent>
    </Sheet>

    <CreateBroadcastDrawer
      v-model:open="createDrawerOpen"
      :error="createError"
      :is-submitting="createMutation.isPending.value"
      @submit="createBroadcast"
    />
  </section>
</template>
