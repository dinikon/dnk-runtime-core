<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Empty, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import {
  feedListReturnTo,
  feedSectionRoutes,
  type FeedSection,
} from "../model/feed.navigation";
import { useFeed } from "../model/feed.queries";
import { useFeedPreview } from "../model/feed-preview.queries";
import { FeedPreviewError } from "../model/feed-preview.types";
import { useDownloadTestCsv } from "../model/use-download-test-csv";
import { feedErrorMessage } from "../model/feed.errors";
import FeedHeader from "../ui/page/FeedHeader.vue";
import FeedSections from "../ui/page/FeedSections.vue";
import FeedPreviewTable from "../ui/results/FeedPreviewTable.vue";

const route = useRoute();
const router = useRouter();
const id = computed(() => String(route.params.id ?? ""));
const returnTo = computed(() => feedListReturnTo(route.query.returnTo));
const feed = useFeed(id);
const version = computed(() =>
  feed.data.value?.status === "ARCHIVED"
    ? null
    : (feed.data.value?.version ?? null),
);
const preview = useFeedPreview(id, version);
const download = useDownloadTestCsv(id, version);
const csv = computed(
  () => feed.data.value?.exportSettings.formatSettings.format === "csv",
);
const csvError = computed(() =>
  download.error.value instanceof FeedPreviewError
    ? download.error.value
    : null,
);
const calculatedAt = computed(() =>
  preview.data.value
    ? new Date(preview.data.value.asOf).toLocaleString("ru-RU")
    : "",
);
const stale = computed(
  () =>
    !!preview.data.value &&
    (preview.isPlaceholderData.value || preview.isError.value),
);
const errorMessage = computed(() => {
  if (feed.error.value) return feedErrorMessage(feed.error.value);
  const error = preview.error.value;
  if (!error) return "";
  return error instanceof FeedPreviewError
    ? error.message
    : "Не удалось загрузить предпросмотр.";
});

function navigate(section: FeedSection): void {
  if (section === "preview") return;
  void router.push({
    name: feedSectionRoutes[section],
    params: { id: id.value },
    query: { returnTo: returnTo.value },
  });
}

function openPublication(publication: string): void {
  void router.push({
    name: feedSectionRoutes.publications,
    params: { id: id.value },
    query: { returnTo: returnTo.value, publication },
  });
}

async function refresh(): Promise<void> {
  const result = await feed.refetch();
  if (
    result.data &&
    result.data.id === id.value &&
    result.data.status !== "ARCHIVED" &&
    !preview.isFetching.value
  )
    await preview.refetch();
}

async function downloadCsv(): Promise<void> {
  const current = feed.data.value;
  if (!current || version.value === null) return;
  const file = await download.execute({
    feedId: current.id,
    expectedVersion: current.version,
  });
  if (!file) return;
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${current.code}.csv`;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
}
</script>

<template>
  <Teleport to="#workspace-page-header" defer>
    <FeedHeader
      :title="feed.data.value?.name ?? 'Предпросмотр фида'"
      :archivable="false"
      :busy="false"
      @back="router.push(returnTo)"
    />
  </Teleport>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Предпросмотр фида</h1>
        <p
          v-if="preview.data.value"
          class="text-sm text-muted-foreground"
          aria-live="polite"
        >
          {{ preview.data.value.rows.length }} из
          {{ preview.data.value.totalEnabled }} включённых позиций ·
          {{ calculatedAt }}
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          :disabled="feed.isFetching.value || preview.isFetching.value"
          @click="refresh"
        >
          {{ preview.isFetching.value ? "Обновляем…" : "Обновить" }}
        </Button>
        <Button
          v-if="csv"
          type="button"
          :disabled="
            download.pending.value || stale || !preview.data.value?.rows.length
          "
          @click="downloadCsv"
        >
          {{ download.pending.value ? "Собираем CSV…" : "Скачать пробный CSV" }}
        </Button>
      </div>
    </header>
    <FeedSections current="preview" @navigate="navigate" />
    <Alert v-if="errorMessage" variant="destructive">
      <AlertDescription>{{ errorMessage }}</AlertDescription>
    </Alert>
    <Alert v-if="download.error.value" variant="destructive">
      <AlertTitle>{{
        csvError?.message ?? "Не удалось скачать CSV."
      }}</AlertTitle>
      <AlertDescription v-if="csvError?.issues.length">
        <ul class="list-disc pl-5">
          <li v-for="(issue, index) in csvError.issues" :key="index">
            <button
              type="button"
              class="text-left underline underline-offset-4"
              @click="openPublication(issue.publicationId)"
            >
              {{ issue.sku ?? issue.variantId ?? issue.itemId }}
            </button>
            <span v-if="issue.fieldName"> · {{ issue.fieldName }}</span>
            — {{ issue.message }}
          </li>
        </ul>
      </AlertDescription>
    </Alert>
    <p v-if="stale" class="text-sm text-muted-foreground" role="status">
      Показан предыдущий результат.
    </p>
    <Empty v-if="feed.data.value?.status === 'ARCHIVED'">
      <EmptyHeader><EmptyTitle>Фид в архиве</EmptyTitle></EmptyHeader>
    </Empty>
    <Skeleton
      v-else-if="
        !preview.data.value &&
        (feed.isPending.value || preview.isFetching.value)
      "
      class="h-32"
      aria-label="Загрузка предпросмотра"
    />
    <template v-else-if="preview.data.value">
      <Empty v-if="!preview.data.value.columns.length">
        <EmptyHeader
          ><EmptyTitle
            >Добавьте экспортируемые поля в схему</EmptyTitle
          ></EmptyHeader
        >
        <Button variant="outline" @click="navigate('schema')"
          >Открыть схему</Button
        >
      </Empty>
      <Empty v-else-if="!preview.data.value.rows.length">
        <EmptyHeader
          ><EmptyTitle>Добавьте или включите товары</EmptyTitle></EmptyHeader
        >
        <Button variant="outline" @click="navigate('publications')"
          >Открыть товары</Button
        >
      </Empty>
      <FeedPreviewTable
        v-else
        :preview="preview.data.value"
        @open-publication="openPublication"
      />
    </template>
  </div>
</template>
