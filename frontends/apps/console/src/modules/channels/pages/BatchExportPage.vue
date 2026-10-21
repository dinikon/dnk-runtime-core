<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { useChannelsContext } from "../model/use-channels-context";
import { useBatchExportQuery } from "../model/queries/use-batch-export-query";
import { useResumeBatchExport } from "../model/mutations/use-resume-batch-export";
import {
  batchStatusLabels,
  exportReason,
} from "../model/batch-export.presentation";
import { channelErrorMessage } from "../model/channels.errors";
import { parsePage } from "../model/channels.url-state";
import { dateLabel } from "../model/channels.presentation";
import { catalogItemLocation } from "@/modules/catalog";
import type { BatchExportItem } from "../model/batch-export.types";
import ChannelsQueryBody from "../ui/ChannelsQueryBody.vue";
import ChannelsPagination from "../ui/ChannelsPagination.vue";
import BatchExportResultsList from "../ui/BatchExportResultsList.vue";
import ExportFeedCard from "../ui/ExportFeedCard.vue";
const route = useRoute(),
  router = useRouter(),
  ctx = useChannelsContext();
const channelId = computed(() => String(route.params.channelId ?? "")),
  runId = computed(() => String(route.params.runId ?? "")),
  page = computed(() => parsePage(route.query.page));
const query = useBatchExportQuery(ctx, () => ({
  runId: runId.value,
  offset: (page.value - 1) * 50,
  limit: 50,
}));
const data = computed(() =>
  query.data.value?.run.channelId === channelId.value
    ? query.data.value
    : undefined,
);
const resume = useResumeBatchExport(ctx),
  error = ref<string | null>(null);
watch([ctx.scope, runId], () => {
  error.value = null;
  resume.reset();
});
async function reconcile(): Promise<void> {
  if (resume.isPending.value) return;
  const current = ctx.capture();
  error.value = null;
  try {
    await resume.mutateAsync(runId.value);
  } catch (e: unknown) {
    if (current()) error.value = channelErrorMessage(e);
  }
}
function setPage(value: number): void {
  void router.replace({
    query: { ...route.query, page: value > 1 ? String(value) : undefined },
  });
}
function openCatalog(item: BatchExportItem): void {
  void router.push(
    catalogItemLocation(item.catalogItemId, Object.keys(item.titles)[0] ?? ""),
  );
}
</script>
<template>
  <main class="flex min-h-0 flex-1 flex-col gap-5 overflow-auto">
    <div>
      <Button
        variant="ghost"
        @click="router.push({ name: 'channel-detail', params: { channelId } })"
        >Назад к каналу</Button
      >
    </div>
    <h1 class="text-2xl font-semibold">Пакетное обновление текстов</h1>
    <ChannelsQueryBody
      :pending="query.isPending.value"
      :has-data="!!data"
      :error="query.error.value ? channelErrorMessage(query.error.value) : null"
      :empty="!data"
      empty-title="Операция не найдена"
      empty-description="Проверьте канал и адрес страницы."
      @retry="query.refetch()"
      ><template v-if="data"
        ><div class="flex flex-wrap items-center gap-3">
          <Badge variant="outline">{{
            batchStatusLabels[data.run.status]
          }}</Badge
          ><span class="text-muted-foreground text-sm"
            >{{ dateLabel(data.run.createdAt) }} ·
            {{
              data.run.trigger === "daily" ? "По расписанию" : "Вручную"
            }}</span
          >
        </div>
        <ExportFeedCard
          v-if="data.feedUrl && data.feedExpiresAt"
          :key="ctx.scope.value + runId"
          :url="data.feedUrl"
          :expires-at="data.feedExpiresAt"
          :file-only="data.run.deliveryMode === 'file'" />
        <Alert v-if="data.run.errorCode"
          ><AlertTitle>Результат операции</AlertTitle
          ><AlertDescription>{{
            exportReason(data.run.errorCode)
          }}</AlertDescription></Alert
        ><Alert v-if="error" variant="destructive"
          ><AlertDescription>{{ error }}</AlertDescription></Alert
        ><Button
          v-if="data.run.status === 'unknown' || data.run.interrupted"
          class="w-fit"
          :disabled="resume.isPending.value"
          @click="reconcile"
          >{{
            resume.isPending.value
              ? "Запрашиваем проверку…"
              : "Проверить результат"
          }}</Button
        >
        <p class="text-muted-foreground text-sm">
          Всего: {{ data.total }} · В XML:
          {{
            (data.run.counts.ready ?? 0) +
            (data.run.counts.verified ?? 0) +
            (data.run.counts.failed ?? 0) +
            (data.run.counts.unknown ?? 0)
          }}
          · Подтверждено: {{ data.run.counts.verified ?? 0 }} · Пропущено:
          {{ data.run.counts.skipped ?? 0 }} · Ошибки:
          {{ data.run.counts.failed ?? 0 }} · Не подтверждено:
          {{ data.run.counts.unknown ?? 0 }}
        </p>
        <p v-if="!data.items.length" class="text-muted-foreground text-sm">
          {{
            data.total
              ? "На этой странице нет позиций."
              : "Нет связанных публикаций с разрешённым экспортом."
          }}
        </p>
        <BatchExportResultsList
          v-else
          :items="data.items"
          @catalog="openCatalog" /><ChannelsPagination
          :page="page"
          :total="data.total"
          :limit="50"
          :pending="query.isFetching.value"
          @change="setPage" /></template
    ></ChannelsQueryBody>
  </main>
</template>
