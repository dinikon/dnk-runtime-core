<script setup lang="ts">
import { computed, onScopeDispose, ref, watch } from "vue";
import { useRoute, useRouter, type LocationQueryRaw } from "vue-router";
import { useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { RefreshCw, Upload, Files, Trash2, HardDrive } from "@lucide/vue";
import type { AxiosProgressEvent } from "axios";
import { useTenantStore } from "@/app/stores/tenant";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
import OffsetPagination from "@/shared/pagination/OffsetPagination.vue";
import { useFileStorage } from "../model/queries";
import { useFilesQuery } from "../model/use-files-query";
import { useTrashQuery } from "../model/use-trash-query";
import { useFilesOverviewQuery } from "../model/use-files-overview-query";
import { useFileMutations } from "../model/use-file-mutations";
import { filesKeys } from "../model/query-keys";
import { fileError } from "../model/errors";
import {
  categoryLabels,
  type FileCategory,
  type FilesFilters as Filters,
  type FileItem,
  type TrashFileItem,
} from "../model/types";
import FilesOverview from "../ui/FilesOverview.vue";
import FilesFilters from "../ui/FilesFilters.vue";
import FilesTable from "../ui/FilesTable.vue";
import TrashFilesTable from "../ui/TrashFilesTable.vue";
import UploadFileDialog from "../ui/UploadFileDialog.vue";
import TrashFileDialog from "../ui/TrashFileDialog.vue";
import PurgeFileDialog from "../ui/PurgeFileDialog.vue";
import FileStoragePage from "./FileStoragePage.vue";
const route = useRoute();
const router = useRouter();
const store = useTenantStore();
const client = useQueryClient();
const tenant = computed(() => store.tenant?.tenant_id ?? "");
const tab = computed(() =>
  route.name === "admin-files-trash"
    ? "trash"
    : route.name === "admin-files-disks"
      ? "disks"
      : "files",
);
function number(value: unknown, fallback: number): number {
  const result = Number(value);
  return Number.isSafeInteger(result) && result > 0 ? result : fallback;
}
const filters = computed<Filters>(() => {
  const category =
    typeof route.query.category === "string" &&
    Object.hasOwn(categoryLabels, route.query.category)
      ? (route.query.category as FileCategory)
      : undefined;
  const ids = route.query.bucket_id;
  const buckets = [
    ...new Set(
      (Array.isArray(ids) ? ids : ids ? [ids] : []).filter(
        (value): value is string => !!value,
      ),
    ),
  ].sort();
  const size = number(route.query.page_size, 20);
  return {
    search:
      typeof route.query.search === "string"
        ? route.query.search.trim().slice(0, 255)
        : "",
    bucket_ids: buckets.slice(0, 50),
    category,
    page: number(route.query.page, 1),
    page_size: [10, 20, 50, 100].includes(size) ? size : 20,
  };
});
const search = ref(filters.value.search);
let timer: ReturnType<typeof setTimeout> | undefined;
let pendingQuery: LocationQueryRaw | null = null;
function updateQuery(patch: LocationQueryRaw): void {
  const queued = pendingQuery !== null;
  pendingQuery = { ...(pendingQuery ?? route.query), ...patch };
  if (!queued)
    queueMicrotask(() => {
      const query = pendingQuery!;
      pendingQuery = null;
      void router.replace({ path: route.path, query });
    });
}
function changeFilters(patch: LocationQueryRaw): void {
  clearTimeout(timer);
  updateQuery({
    search: search.value.trim() || undefined,
    ...patch,
    page: undefined,
  });
}
function searchChanged(value: string): void {
  search.value = value;
  clearTimeout(timer);
  timer = setTimeout(() => changeFilters({}), 300);
}
watch(
  () => filters.value.search,
  (value) => {
    clearTimeout(timer);
    search.value = value;
  },
);
onScopeDispose(() => clearTimeout(timer));
function reset(): void {
  search.value = "";
  changeFilters({
    search: undefined,
    bucket_id: undefined,
    category: undefined,
  });
}
function switchTab(value: unknown): void {
  clearTimeout(timer);
  const name =
    value === "trash"
      ? "admin-files-trash"
      : value === "disks"
        ? "admin-files-disks"
        : "admin-files";
  void router.push({
    name,
    query: {
      ...route.query,
      search: search.value.trim() || undefined,
      page: undefined,
    },
  });
}
const storage = useFileStorage();
const active = useFilesQuery(
  filters,
  computed(() => tab.value === "files"),
);
const trash = useTrashQuery(
  filters,
  computed(() => tab.value === "trash"),
);
const overview = useFilesOverviewQuery(
  computed(() => filters.value.bucket_ids),
);
const mutations = useFileMutations();
const data = computed(() =>
  tab.value === "trash" ? trash.data.value : active.data.value,
);
const loading = computed(() =>
  tab.value === "trash" ? trash.isPending.value : active.isPending.value,
);
const error = computed(() =>
  tab.value === "trash" ? trash.error.value : active.error.value,
);
const fetching = computed(() =>
  tab.value === "trash" ? trash.isFetching.value : active.isFetching.value,
);
const busy = computed(
  () =>
    mutations.upload.isPending.value ||
    mutations.trash.isPending.value ||
    mutations.restore.isPending.value ||
    mutations.purge.isPending.value,
);
const filtered = computed(
  () =>
    !!filters.value.search ||
    !!filters.value.bucket_ids.length ||
    !!filters.value.category,
);
const uploadOpen = ref(false);
const trashTarget = ref<FileItem | null>(null);
const purgeTarget = ref<FileItem | null>(null);
const actionError = ref("");
watch(tenant, () => {
  uploadOpen.value = false;
  trashTarget.value = null;
  purgeTarget.value = null;
  actionError.value = "";
});
watch([trashTarget, purgeTarget], () => {
  actionError.value = "";
});
watch([data, fetching], ([value, isFetching]) => {
  if (
    value &&
    !isFetching &&
    value.total < (filters.value.page - 1) * filters.value.page_size + 1 &&
    filters.value.page > 1
  )
    updateQuery({
      page: String(
        Math.max(1, Math.ceil(value.total / filters.value.page_size)),
      ),
    });
});
// Refresh overview after polling physically removes a pending file.
watch(trash.dataUpdatedAt, (value, previous) => {
  if (value && previous && tab.value === "trash")
    void client.invalidateQueries({
      queryKey: ["files", tenant.value, "overview"],
    });
});
async function refresh(): Promise<void> {
  await client.invalidateQueries({ queryKey: filesKeys.tenant(tenant.value) });
}
async function upload(
  file: File,
  bucketId: string,
  onProgress: (event: AxiosProgressEvent) => void,
): Promise<void> {
  await mutations.upload.mutateAsync({
    tenant: tenant.value,
    file,
    bucketId,
    onProgress,
  });
}
async function confirmTrash(): Promise<void> {
  if (!trashTarget.value || busy.value) return;
  try {
    await mutations.trash.mutateAsync({
      tenant: tenant.value,
      id: trashTarget.value.file_id,
    });
    trashTarget.value = null;
  } catch (cause) {
    actionError.value = fileError(cause);
  }
}
async function confirmPurge(): Promise<void> {
  if (!purgeTarget.value || busy.value) return;
  try {
    await mutations.purge.mutateAsync({
      tenant: tenant.value,
      id: purgeTarget.value.file_id,
    });
    purgeTarget.value = null;
  } catch (cause) {
    actionError.value = fileError(cause);
  }
}
async function restore(file: TrashFileItem): Promise<void> {
  if (busy.value) return;
  try {
    await mutations.restore.mutateAsync({
      tenant: tenant.value,
      id: file.file_id,
    });
  } catch (cause) {
    toast.error(fileError(cause));
    await refresh();
  }
}
</script>
<template>
  <div lang="ru" class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Файлы</h1>
        <p class="text-sm text-muted-foreground">
          Файлы рабочего пространства на всех подключённых дисках
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <Button variant="outline" :disabled="fetching || busy" @click="refresh"
          ><RefreshCw data-icon="inline-start" />Обновить</Button
        ><Button
          :disabled="
            busy ||
            !storage.buckets.data.value?.some((item) => item.status === 'ready')
          "
          @click="uploadOpen = true"
          ><Upload data-icon="inline-start" />Загрузить файл</Button
        >
      </div>
    </header>
    <Alert
      v-if="store.tenant && !tenant && !store.isResolvingTenant"
      variant="destructive"
      ><AlertTitle>Рабочее пространство недоступно</AlertTitle
      ><AlertDescription
        >Не удалось определить рабочее пространство.<Button
          variant="outline"
          size="sm"
          @click="store.resolveTenant()"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <template v-else>
      <div
        v-if="overview.isPending.value"
        class="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4"
        aria-label="Загрузка сводки"
      >
        <Skeleton v-for="i in 4" :key="i" class="h-44" />
      </div>
      <Alert v-else-if="overview.isError.value" variant="destructive"
        ><AlertTitle>Не удалось загрузить сводку</AlertTitle
        ><AlertDescription
          >{{ fileError(overview.error.value)
          }}<Button variant="outline" size="sm" @click="overview.refetch()"
            >Повторить</Button
          ></AlertDescription
        ></Alert
      >
      <FilesOverview
        v-else-if="overview.data.value"
        :data="overview.data.value"
        :selected="filters.category"
        @select="
          changeFilters({
            category: filters.category === $event ? undefined : $event,
          })
        "
      />
      <Tabs :model-value="tab" @update:model-value="switchTab"
        ><TabsList
          aria-label="Разделы файлового менеджера"
          class="w-full sm:w-fit"
          ><TabsTrigger value="files"><Files />Файлы</TabsTrigger
          ><TabsTrigger value="trash"
            ><Trash2 />Корзина<Badge
              v-if="overview.data.value"
              variant="secondary"
              >{{ overview.data.value.trashed_count }}</Badge
            ></TabsTrigger
          ><TabsTrigger value="disks"><HardDrive />Диски</TabsTrigger></TabsList
        >
        <TabsContent :value="tab" class="min-w-0">
          <FileStoragePage v-if="tab === 'disks'" />
          <Card v-else
            ><CardHeader
              ><CardTitle>{{
                tab === "trash" ? "Корзина" : "Все файлы"
              }}</CardTitle
              ><CardDescription>{{
                tab === "trash"
                  ? "Файлы хранятся 30 дней. Окончательное удаление выполняется в фоне."
                  : "Поиск по названию и фильтры по дискам и типу файла"
              }}</CardDescription></CardHeader
            ><CardContent class="flex min-w-0 flex-col gap-4">
              <FilesFilters
                :search="search"
                :buckets="storage.buckets.data.value ?? []"
                :selected="filters.bucket_ids"
                :category="filters.category"
                @search="searchChanged"
                @buckets="
                  changeFilters({
                    bucket_id: $event.length ? $event : undefined,
                  })
                "
                @category="changeFilters({ category: $event })"
                @reset="reset"
              />
              <Alert v-if="storage.buckets.isError.value" variant="destructive"
                ><AlertTitle>Не удалось получить диски</AlertTitle
                ><AlertDescription
                  ><Button
                    variant="outline"
                    size="sm"
                    @click="storage.buckets.refetch()"
                    >Повторить</Button
                  ></AlertDescription
                ></Alert
              >
              <Skeleton
                v-if="loading"
                class="h-64"
                aria-label="Загрузка файлов"
              />
              <Alert v-else-if="error" variant="destructive"
                ><AlertTitle>Не удалось загрузить список</AlertTitle
                ><AlertDescription
                  >{{ fileError(error)
                  }}<Button variant="outline" size="sm" @click="refresh"
                    >Повторить</Button
                  ></AlertDescription
                ></Alert
              >
              <template v-else-if="data"
                ><div :aria-busy="fetching">
                  <Empty v-if="!data.items.length"
                    ><EmptyHeader
                      ><EmptyTitle>{{
                        filtered
                          ? "Файлы не найдены"
                          : tab === "trash"
                            ? "Корзина пуста"
                            : "Файлов пока нет"
                      }}</EmptyTitle
                      ><EmptyDescription>{{
                        filtered
                          ? "Попробуйте изменить запрос или сбросить фильтры."
                          : tab === "trash"
                            ? "Удалённые файлы появятся здесь."
                            : "Загрузите первый файл на готовый диск."
                      }}</EmptyDescription></EmptyHeader
                    ><Button v-if="filtered" variant="outline" @click="reset"
                      >Сбросить фильтры</Button
                    ></Empty
                  ><TrashFilesTable
                    v-else-if="tab === 'trash'"
                    :items="trash.data.value?.items ?? []"
                    :busy="busy || fetching"
                    @restore="restore"
                    @purge="purgeTarget = $event"
                  /><FilesTable
                    v-else
                    :items="active.data.value?.items ?? []"
                    :busy="busy || fetching"
                    @trash="trashTarget = $event"
                  />
                </div>
                <OffsetPagination
                  locale="ru"
                  :page="filters.page"
                  :limit="filters.page_size"
                  :total="data.total"
                  :disabled="fetching || busy"
                  @update:page="updateQuery({ page: String($event) })"
                  @update:limit="changeFilters({ page_size: String($event) })"
              /></template> </CardContent
          ></Card> </TabsContent
      ></Tabs>
      <UploadFileDialog
        :key="tenant"
        :open="uploadOpen"
        :buckets="storage.buckets.data.value ?? []"
        :busy="mutations.upload.isPending.value"
        :submit="upload"
        :refresh="refresh"
        @close="uploadOpen = false"
      />
      <TrashFileDialog
        :file="trashTarget"
        :busy="mutations.trash.isPending.value"
        :error="actionError"
        @close="trashTarget = null"
        @confirm="confirmTrash"
      />
      <PurgeFileDialog
        :file="purgeTarget"
        :busy="mutations.purge.isPending.value"
        :error="actionError"
        @close="purgeTarget = null"
        @confirm="confirmPurge"
      />
    </template>
  </div>
</template>
