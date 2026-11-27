<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  feedListReturnTo,
  feedSectionRoutes,
  type FeedSection,
} from "../model/feed.navigation";
import { feedErrorMessage } from "../model/feed.errors";
import { FeedRequestError } from "../model/feed-request-error";
import { useFeed } from "../model/feed.queries";
import { feedKeys } from "../model/feed.query-keys";
import { useFeedScope } from "../model/use-feed-scope";
import { useFeedAccessEditor } from "../model/use-feed-access-editor";
import type { FeedAccessMode } from "../model/feed-access.types";
import {
  exportKeys,
  useFeedExport,
  useLatestFeedExportIssues,
} from "../model/feed-export.queries";
import {
  useRequestFeedRefresh,
  useRotateFeedLink,
} from "../model/feed-export.mutations";
import type {
  ExportIssueSeverity,
  FeedExportState,
} from "../model/feed-export.types";
import FeedHeader from "../ui/page/FeedHeader.vue";
import FeedSections from "../ui/page/FeedSections.vue";
import FeedExportPanel from "../ui/results/FeedExportPanel.vue";
import FeedAccessPanel from "../ui/forms/FeedAccessPanel.vue";

const route = useRoute();
const router = useRouter();
const cache = useQueryClient();
const scope = useFeedScope();
const id = computed(() => String(route.params.id ?? ""));
const returnTo = computed(() => feedListReturnTo(route.query.returnTo));
const feed = useFeed(id);
const state = useFeedExport(id);
const refresh = useRequestFeedRefresh();
const rotate = useRotateFeedLink();
const canManageAccess = computed(() => state.data.value?.canManageAccess === true);
const access = useFeedAccessEditor(id, canManageAccess);
const accessContext = computed(() => JSON.stringify([scope.value, id.value]));
const busy = computed(() => refresh.pending.value || rotate.pending.value || access.pending.value);
function errorText(error: unknown): string {
  if (error instanceof FeedRequestError && error.issues[0]) {
    return error.issues[0].message;
  }
  return error ? feedErrorMessage(error) : "";
}
const actionError = computed(() => errorText(refresh.error.value || rotate.error.value));
const severity = ref<ExportIssueSeverity | "">("");
const offset = ref(0);
const reportedAt = computed(() => state.data.value?.report?.completedAt);
const issues = useLatestFeedExportIssues(id, reportedAt, severity, offset);

watch([id, reportedAt, scope], () => {
  severity.value = "";
  offset.value = 0;
});
watch(
  () => state.data.value?.feedVersion,
  (next) => {
    if (next !== undefined && feed.data.value?.version !== next) {
      void cache.invalidateQueries({
        queryKey: feedKeys.detail(scope.value, id.value),
      });
    }
  },
);

function navigate(section: FeedSection): void {
  if (section === "export") return;
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
function filter(value: ExportIssueSeverity | ""): void {
  severity.value = value;
  offset.value = 0;
}
async function copy(url: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(url);
    toast.success("Скопировано.");
  } catch {
    toast.error("Не удалось скопировать. Выделите текст и скопируйте вручную.");
  }
}
async function changeAccessMode(mode: FeedAccessMode): Promise<void> {
  const current = state.data.value;
  if (!current?.canManageAccess || current.accessMode === mode || busy.value) return;
  const context = accessContext.value;
  const key = exportKeys.state(scope.value, id.value);
  const changed = await access.change(mode, current.feedVersion);
  if (context !== accessContext.value) return;
  if (changed) {
    cache.setQueryData<FeedExportState>(key, (previous) => previous && { ...previous, ...changed });
  }
  await state.refetch();
}

async function requestRefresh(): Promise<void> {
  const current = state.data.value;
  if (!current?.canRefresh || current.task || busy.value) return;
  rotate.error.value = undefined;
  const key = exportKeys.state(scope.value, id.value);
  const result = await refresh.execute({
    feedId: id.value,
    version: current.feedVersion,
  });
  if (result && key[5] === id.value) {
    cache.setQueryData<FeedExportState>(
      key,
      (previous) => previous && { ...previous, task: result.value },
    );
  }
  await state.refetch();
}
async function replaceLink(): Promise<void> {
  const current = state.data.value;
  if (!current?.canRotate || busy.value) return;
  refresh.error.value = undefined;
  const key = exportKeys.state(scope.value, id.value);
  const result = await rotate.execute({
    feedId: id.value,
    version: current.feedVersion,
  });
  if (result && key[5] === id.value) {
    cache.setQueryData<FeedExportState>(key, (previous) =>
      previous?.active
        ? {
            ...previous,
            feedVersion: result.value.feedVersion,
            active: { ...previous.active, url: result.value.url },
          }
        : previous,
    );
  }
  await state.refetch();
}
</script>
<template>
  <Teleport to="#workspace-page-header" defer>
    <FeedHeader
      :title="feed.data.value?.name ?? 'Экспорт фида'"
      :archivable="false"
      :busy="busy"
      @back="router.push(returnTo)"
    />
  </Teleport>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto pb-6">
    <h1 class="text-2xl font-semibold">Экспорт</h1>
    <FeedSections current="export" @navigate="navigate" />
    <div v-if="state.error.value" class="flex flex-wrap items-center gap-2">
      <p role="alert" class="text-sm text-destructive">
        {{ feedErrorMessage(state.error.value) }}
      </p>
      <Button type="button" size="sm" variant="outline" @click="state.refetch()"
        >Повторить</Button
      >
    </div>
    <FeedExportPanel
      v-else-if="state.data.value"
      :data="state.data.value"
      :configured-format="feed.data.value?.exportSettings.formatSettings.format"
      :issues="issues.data.value"
      :issues-error="
        issues.error.value ? feedErrorMessage(issues.error.value) : ''
      "
      :issues-loading="issues.isLoading.value"
      :severity="severity"
      :offset="offset"
      :busy="busy"
      :error="actionError"
      @copy="copy"
      @refresh="requestRefresh"
      @rotate="replaceLink"
      @filter="filter"
      @page="offset = $event"
      @open-publication="openPublication"
      @retry-issues="issues.refetch()"
    >
      <template #access>
        <FeedAccessPanel
          v-if="state.data.value.canManageAccess"
          :key="accessContext"
          :mode="state.data.value.accessMode"
          :tokens="access.tokens.data.value"
          :loading="access.tokens.isLoading.value"
          :load-error="errorText(access.tokens.error.value)"
          :action-error="errorText(access.error.value)"
          :busy="busy"
          :issued="access.issued.value"
          :download-url="state.data.value.active?.url"
          @change-mode="changeAccessMode"
          @issue="access.issue"
          @revoke="access.revoke"
          @dismiss="access.dismiss"
          @retry="access.tokens.refetch()"
          @copy="copy"
        />
      </template>
    </FeedExportPanel>
    <Skeleton v-else class="h-32 w-full" aria-label="Загрузка экспорта" />
  </div>
</template>
