<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter, onBeforeRouteLeave } from "vue-router";
import { toast } from "vue-sonner";
import { Button } from "@/components/ui/button";
import { OffsetPagination } from "@/shared/pagination";
import FeedsToolbar from "../ui/page/FeedsToolbar.vue";
import FeedsBody from "../ui/results/FeedsBody.vue";
import ArchiveFeedDialog from "../ui/forms/ArchiveFeedDialog.vue";
import { useFeedsPageState } from "../model/use-feeds-page-state";
import { useFeeds } from "../model/feed.queries";
import { useFeedScope } from "../model/use-feed-scope";
import { useArchiveFeed } from "../model/use-archive-feed";
import { feedErrorMessage } from "../model/feed.errors";
import { lastFeedOffset } from "../model/feed.navigation";
import { FeedApiError, type FeedListItem } from "../model/feed.types";
const router = useRouter(),
  route = useRoute(),
  state = useFeedsPageState(),
  scope = useFeedScope();
const query = useFeeds(state.filters),
  archive = useArchiveFeed(),
  target = ref<FeedListItem | null>(null);
const error = computed(() =>
  query.error.value ? feedErrorMessage(query.error.value) : "",
);
const archiveError = computed(() =>
  archive.error.value ? feedErrorMessage(archive.error.value) : "",
);
const archiveConflict = computed(
  () =>
    archive.error.value instanceof FeedApiError &&
    archive.error.value.status === 409,
);
onBeforeRouteLeave(() => !archive.pending.value);
watch(
  scope,
  () => {
    target.value = null;
  },
  { flush: "sync" },
);
watch(query.data, (page) => {
  if (
    page &&
    state.filters.value.offset > lastFeedOffset(page.total, page.limit)
  )
    state.setOffset(lastFeedOffset(page.total, page.limit));
});
function open(id: string): void {
  if (archive.pending.value) return;
  void router.push({
    name: "feed-detail",
    params: { id },
    query: { returnTo: route.fullPath },
  });
}
function create(): void {
  if (archive.pending.value) return;
  void router.push({ name: "feed-new", query: { returnTo: route.fullPath } });
}
function askArchive(feed: FeedListItem): void {
  if (archive.pending.value) return;
  archive.error.value = undefined;
  target.value = { ...feed };
}
async function confirmArchive(): Promise<void> {
  if (!target.value || archiveConflict.value) return;
  const result = await archive.execute({
    id: target.value.id,
    expectedVersion: target.value.version,
  });
  if (result) {
    target.value = null;
    toast.success("Фид перемещён в архив");
    await query.refetch();
  }
}
</script>
<template>
  <div
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto lg:overflow-hidden"
  >
    <header class="flex shrink-0 flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">Фиды</h1>
      <Button :disabled="archive.pending.value" @click="create"
        >Создать фид</Button
      >
    </header>
    <FeedsToolbar :filters="state.filters.value" @filter="state.setFilter" />
    <FeedsBody
      :loading="query.isPending.value"
      :error="error"
      :items="query.data.value?.items ?? []"
      :filtered="!!(state.filters.value.search || state.filters.value.status)"
      :busy="archive.pending.value"
      @retry="query.refetch()"
      @create="create"
      @reset="state.reset"
      @open="open"
      @archive="askArchive"
    />
    <footer
      v-if="query.data.value"
      class="shrink-0"
      aria-label="Навигация по фидам"
    >
      <OffsetPagination
        :page="Math.floor(state.filters.value.offset / 50) + 1"
        :limit="50"
        :limit-options="[50]"
        :total="query.data.value.total"
        :disabled="query.isFetching.value"
        locale="ru"
        @change="state.setOffset(($event.page - 1) * 50)"
      />
    </footer>
    <ArchiveFeedDialog
      :open="!!target"
      :name="target?.name ?? ''"
      :code="target?.code ?? ''"
      :busy="archive.pending.value"
      :error="archiveError"
      :conflicted="archiveConflict"
      @update:open="!$event && (target = null)"
      @confirm="confirmArchive"
    />
  </div>
</template>
