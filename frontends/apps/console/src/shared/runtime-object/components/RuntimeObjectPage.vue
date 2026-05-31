<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { isAxiosError } from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { Filter, Plus, RefreshCcw, X } from "lucide-vue-next";
import { toast } from "vue-sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
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
import {
  areRuntimeFiltersEqual,
  areRuntimeSortsEqual,
  RUNTIME_OBJECT_PAGE_SIZES,
  sanitizeRuntimeFilterForFields,
  sanitizeRuntimeSortForFields,
  useRuntimeObjectQueryState,
} from "@/shared/runtime-object/composables/use-runtime-object-query-state";
import type {
  RuntimeFilter,
  RuntimeObjectMutationPayload,
  RuntimeObjectRecord,
  RuntimeObjectResource,
  RuntimeObjectSearchRequest,
  RuntimeSort,
} from "@/shared/runtime-object";
import RuntimeObjectFilterBuilder from "@/shared/runtime-object/filters/RuntimeObjectFilterBuilder.vue";
import RuntimeObjectForm from "@/shared/runtime-object/form/RuntimeObjectForm.vue";
import RuntimeObjectTable from "@/shared/runtime-object/table/RuntimeObjectTable.vue";

const props = defineProps<{
  resource: RuntimeObjectResource;
}>();

const queryClient = useQueryClient();
const queryState = useRuntimeObjectQueryState();

const filterSheetOpen = ref(false);
const formSheetOpen = ref(false);
const formMode = ref<"create" | "edit">("create");
const activeRecord = ref<RuntimeObjectRecord | null>(null);
const formError = ref<string | null>(null);
const tableError = ref<string | null>(null);
const deleteDialogOpen = ref(false);
const recordPendingDelete = ref<RuntimeObjectRecord | null>(null);

const schemaQuery = useQuery({
  queryKey: computed(() => ["runtime-object", props.resource.key, "schema"]),
  queryFn: () => props.resource.describeFields(),
  retry: false,
});

const schema = computed(() => schemaQuery.data.value);
const fields = computed(() => schema.value?.fields ?? []);
const filter = computed(() =>
  sanitizeRuntimeFilterForFields(queryState.filter.value, fields.value),
);
const sort = computed(() =>
  sanitizeRuntimeSortForFields(queryState.sort.value, fields.value),
);
const limit = queryState.limit;
const offset = queryState.offset;

const searchPayload = computed<RuntimeObjectSearchRequest>(() => ({
  filter: filter.value,
  sort: sort.value,
  pagination: {
    limit: limit.value,
    offset: offset.value,
  },
}));

const searchQuery = useQuery({
  queryKey: computed(() => [
    "runtime-object",
    props.resource.key,
    "search",
    searchPayload.value,
  ]),
  queryFn: () => props.resource.search(searchPayload.value),
  enabled: computed(() => !!schemaQuery.data.value),
  retry: false,
});

const createMutation = useMutation({
  mutationFn: (payload: RuntimeObjectMutationPayload) =>
    props.resource.create(payload),
});

const updateMutation = useMutation({
  mutationFn: ({
    id,
    payload,
  }: {
    id: string;
    payload: RuntimeObjectMutationPayload;
  }) => props.resource.update(id, payload),
});

const deleteMutation = useMutation({
  mutationFn: (id: string) => props.resource.delete(id),
});

const records = computed<RuntimeObjectRecord[]>(
  () => (searchQuery.data.value?.data ?? []) as RuntimeObjectRecord[],
);
const pagination = computed(() => searchQuery.data.value?.pagination);
const total = computed(() => pagination.value?.total ?? 0);
const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1);
const pageStart = computed(() => (total.value === 0 ? 0 : offset.value + 1));
const pageEnd = computed(() =>
  Math.min(offset.value + limit.value, total.value),
);
const canGoPrevious = computed(() => offset.value > 0);
const canGoNext = computed(() => offset.value + limit.value < total.value);
const isSaving = computed(
  () => createMutation.isPending.value || updateMutation.isPending.value,
);
const filterCount = computed(() => countFilterConditions(filter.value));
const hasFilterableFields = computed(() =>
  fields.value.some((field) => field.filter.enabled),
);
const pageTitle = computed(
  () => schema.value?.object.plural_label ?? "Records",
);
const pageDescription = computed(
  () => schema.value?.object.description ?? "Runtime object records.",
);

watch(
  [fields, queryState.filter, queryState.sort, queryState.hasInvalidQuery],
  () => {
    if (!schema.value) {
      return;
    }

    if (
      queryState.hasInvalidQuery.value ||
      !areRuntimeFiltersEqual(filter.value, queryState.filter.value) ||
      !areRuntimeSortsEqual(sort.value, queryState.sort.value)
    ) {
      void queryState.replaceState({
        filter: filter.value,
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

function applyFilter(nextFilter: RuntimeFilter | null) {
  tableError.value = null;
  filterSheetOpen.value = false;
  void queryState.pushState({ filter: nextFilter, offset: 0 });
}

function resetFilters() {
  tableError.value = null;
  void queryState.pushState({ filter: null, offset: 0 });
}

function handleSortChange(nextSort: RuntimeSort[]) {
  tableError.value = null;
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

function openCreateForm() {
  formMode.value = "create";
  activeRecord.value = null;
  formError.value = null;
  formSheetOpen.value = true;
}

function openEditForm(record: RuntimeObjectRecord) {
  formMode.value = "edit";
  activeRecord.value = record;
  formError.value = null;
  formSheetOpen.value = true;
}

function requestDelete(record: RuntimeObjectRecord) {
  tableError.value = null;
  recordPendingDelete.value = record;
  deleteDialogOpen.value = true;
}

async function submitForm(payload: RuntimeObjectMutationPayload) {
  formError.value = null;

  try {
    if (formMode.value === "create") {
      await createMutation.mutateAsync(payload);
      toast.success(
        `${schema.value?.object.singular_label ?? "Record"} created.`,
      );
    } else if (activeRecord.value) {
      await updateMutation.mutateAsync({
        id: activeRecord.value.id,
        payload,
      });
      toast.success(
        `${schema.value?.object.singular_label ?? "Record"} updated.`,
      );
    }

    formSheetOpen.value = false;
    activeRecord.value = null;
    await refreshSearch();
  } catch (error) {
    formError.value = apiErrorMessage(error);
  }
}

async function confirmDelete() {
  if (!recordPendingDelete.value) {
    return;
  }

  tableError.value = null;

  try {
    await deleteMutation.mutateAsync(recordPendingDelete.value.id);
    toast.success(
      `${schema.value?.object.singular_label ?? "Record"} deleted.`,
    );
    recordPendingDelete.value = null;
    await refreshSearch();
  } catch (error) {
    tableError.value = apiErrorMessage(error);
  }
}

async function refreshSearch() {
  await queryClient.invalidateQueries({
    queryKey: ["runtime-object", props.resource.key, "search"],
  });
}

function apiErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }

    if (detail !== undefined) {
      return JSON.stringify(detail);
    }

    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unexpected error.";
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
          :disabled="searchQuery.isFetching.value"
          @click="searchQuery.refetch()"
        >
          <RefreshCcw
            class="size-4"
            :class="{ 'animate-spin': searchQuery.isFetching.value }"
          />
          Refresh
        </Button>
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
          v-if="hasFilterableFields && filterCount > 0"
          type="button"
          variant="outline"
          @click="resetFilters"
        >
          <X class="size-4" />
          Reset filters
        </Button>
        <Button type="button" :disabled="!schema" @click="openCreateForm">
          <Plus class="size-4" />
          New {{ schema?.object.singular_label ?? "Record" }}
        </Button>
      </div>
    </div>

    <Alert v-if="schemaQuery.error.value" variant="destructive">
      <AlertDescription>{{
        apiErrorMessage(schemaQuery.error.value)
      }}</AlertDescription>
    </Alert>
    <Alert v-if="searchQuery.error.value || tableError" variant="destructive">
      <AlertDescription>
        {{ tableError ?? apiErrorMessage(searchQuery.error.value) }}
      </AlertDescription>
    </Alert>

    <RuntimeObjectTable
      v-if="schema"
      class="flex-1"
      :fields="fields"
      :records="records"
      :sort="sort"
      :is-loading="searchQuery.isLoading.value || searchQuery.isFetching.value"
      @sort-change="handleSortChange"
      @edit="openEditForm"
      @delete="requestDelete"
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
            :disabled="!canGoPrevious || searchQuery.isFetching.value"
            @click="goPrevious"
          >
            Previous
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="!canGoNext || searchQuery.isFetching.value"
            @click="goNext"
          >
            Next
          </Button>
        </div>
      </Pagination>
    </div>

    <Sheet v-if="hasFilterableFields" v-model:open="filterSheetOpen">
      <SheetContent class="sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>Filters</SheetTitle>
          <SheetDescription>
            Build a server-side filter from available field metadata.
          </SheetDescription>
        </SheetHeader>
        <RuntimeObjectFilterBuilder
          :fields="fields"
          :model-value="filter"
          @apply="applyFilter"
          @cancel="filterSheetOpen = false"
        />
      </SheetContent>
    </Sheet>

    <Sheet v-model:open="formSheetOpen">
      <SheetContent class="sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>
            {{
              formMode === "create"
                ? `New ${schema?.object.singular_label ?? "Record"}`
                : `Edit ${schema?.object.singular_label ?? "Record"}`
            }}
          </SheetTitle>
          <SheetDescription>
            Fields are generated from runtime object metadata.
          </SheetDescription>
        </SheetHeader>
        <RuntimeObjectForm
          v-if="schema"
          :fields="fields"
          :record="activeRecord"
          :mode="formMode"
          :is-submitting="isSaving"
          :error="formError"
          @submit="submitForm"
          @cancel="formSheetOpen = false"
        />
      </SheetContent>
    </Sheet>

    <AlertDialog v-model:open="deleteDialogOpen">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete record?</AlertDialogTitle>
          <AlertDialogDescription>
            This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel :disabled="deleteMutation.isPending.value">
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            :disabled="deleteMutation.isPending.value"
            @click="confirmDelete"
          >
            {{ deleteMutation.isPending.value ? "Deleting..." : "Delete" }}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </section>
</template>
