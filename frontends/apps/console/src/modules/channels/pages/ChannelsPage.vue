<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { OffsetPagination } from "@/shared/pagination";
import ChannelsBody from "../ui/ChannelsBody.vue";
import ChannelsToolbar from "../ui/ChannelsToolbar.vue";
import { useChannelsPageState } from "../model/use-channels-page-state";
import { useChannels, useChannelPlatforms } from "../model/channel.queries";
import { channelErrorMessage } from "../model/channel.errors";
const router = useRouter(),
  route = useRoute(),
  state = useChannelsPageState();
const query = useChannels(state.filters),
  platforms = useChannelPlatforms();
const error = computed(() =>
  query.error.value || platforms.error.value
    ? channelErrorMessage(query.error.value ?? platforms.error.value)
    : "",
);
const filtered = computed(
  () =>
    !!(
      state.filters.value.search ||
      state.filters.value.platformKind ||
      state.filters.value.status
    ),
);
function open(id: string): void {
  void router.push({
    name: "channel-detail",
    params: { id },
    query: { returnTo: route.fullPath },
  });
}
function create(): void {
  void router.push({
    name: "channel-new",
    query: { returnTo: route.fullPath },
  });
}
function reset(): void {
  void router.replace({
    query: {
      ...route.query,
      q: undefined,
      platform: undefined,
      status: undefined,
      offset: undefined,
    },
    hash: route.hash,
  });
}
</script>
<template>
  <div
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto lg:overflow-hidden"
  >
    <header class="flex shrink-0 flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">Подключения</h1>
      <Button @click="create">Подключить магазин</Button>
    </header>
    <ChannelsToolbar
      :filters="state.filters.value"
      :platforms="platforms.data.value ?? []"
      @filter="state.setFilter"
    />
    <ChannelsBody
      :loading="query.isPending.value"
      :error="error"
      :items="query.data.value?.items ?? []"
      :platforms="platforms.data.value ?? []"
      :filtered="filtered"
      :out-of-range="state.filters.value.offset > 0"
      @retry="
        query.refetch();
        platforms.refetch();
      "
      @open="open"
      @create="create"
      @reset="reset"
      @first-page="state.setOffset(0)"
    />
    <footer
      v-if="query.data.value"
      class="shrink-0"
      aria-label="Навигация по подключениям"
    >
      <OffsetPagination
        :page="Math.floor(state.filters.value.offset / 50) + 1"
        :limit="50"
        :limit-options="[50]"
        :total="query.data.value.total"
        locale="ru"
        @change="state.setOffset(($event.page - 1) * 50)"
      />
    </footer>
  </div>
</template>
