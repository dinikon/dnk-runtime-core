<script setup lang="ts">
import { computed, watch, ref, onBeforeUnmount } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQueryClient } from "@tanstack/vue-query";
import type { PageHeaderAction } from "@/components/custom-ui/page-header";
import { toast } from "vue-sonner";
import { useCreatePublicationCatalog } from "../model/use-create-publication-catalog";
import { publicationCatalogError } from "../model/catalog-creation.errors";
import type { PublicationCreationState } from "../model/catalog-creation.types";
import { useChannel } from "../model/channel.queries";
import { useChannelScope } from "../model/use-channel-scope";
import {
  usePublicationSync,
  usePublications,
} from "../model/publication.queries";
import { useStartPublicationSync } from "../model/use-start-publication-sync";
import { usePublicationsPageState } from "../model/use-publications-page-state";
import { publicationKeys } from "../model/publication.query-keys";
import { channelErrorMessage } from "../model/channel.errors";
import PublicationSyncStatus from "../ui/PublicationSyncStatus.vue";
import PublicationsToolbar from "../ui/PublicationsToolbar.vue";
import PublicationsBody from "../ui/PublicationsBody.vue";
import ChannelHeader from "../ui/ChannelHeader.vue";
import PublicationsFooter from "../ui/PublicationsFooter.vue";
const route = useRoute(),
  router = useRouter(),
  client = useQueryClient(),
  scope = useChannelScope();
const id = computed(() => String(route.params.id ?? ""));
const creation = useCreatePublicationCatalog();
const creationState = ref<Record<string, PublicationCreationState>>({});
let mounted = true;
onBeforeUnmount(() => {
  mounted = false;
});
watch(
  () => JSON.stringify([scope.value, id.value]),
  () => {
    creationState.value = {};
  },
);
function openCatalog(itemId: string): void {
  void router.push({
    path: `/catalog/items/${encodeURIComponent(itemId)}`,
    query: {
      locale:
        publications.data.value?.locale ||
        state.filters.value.locale ||
        undefined,
    },
  });
}
async function createCatalog(publicationId: string): Promise<void> {
  if (creationState.value[publicationId]?.pending) return;
  const captured = JSON.stringify([scope.value, id.value]);
  creationState.value[publicationId] = {
    pending: true,
    error: "",
    catalogItemId: null,
    warnings: [],
  };
  const relevant = () =>
    mounted && captured === JSON.stringify([scope.value, id.value]);
  try {
    const result = await creation.mutateAsync({
      channelId: id.value,
      publicationId,
    });
    if (!relevant()) return;
    creationState.value[publicationId] = {
      pending: false,
      error: "",
      catalogItemId: result.catalogItemId,
      warnings: result.warnings,
    };
    toast.success(
      result.created
        ? "Товар создан и связан с публикацией"
        : "Публикация уже связана с товаром",
      {
        description: result.warnings.join(" "),
        action: {
          label: "Открыть товар",
          onClick: () => {
            if (relevant()) openCatalog(result.catalogItemId);
          },
        },
      },
    );
  } catch (cause) {
    if (relevant())
      creationState.value[publicationId] = {
        pending: false,
        error: publicationCatalogError(cause),
        catalogItemId: null,
        warnings: [],
      };
  }
}

const channel = useChannel(id),
  state = usePublicationsPageState(channel.data),
  sync = usePublicationSync(id),
  start = useStartPublicationSync();
const active = computed(
  () =>
    !!sync.data.value &&
    ["queued", "running"].includes(sync.data.value.status) &&
    !sync.data.value.recoveryRequired,
);
const publications = usePublications(id, state.filters, active);
const syncDisabled = computed(
  () => !channel.data.value?.availableCapabilities.includes("publications"),
);
const actions = computed<PageHeaderAction[]>(() => [
  { id: "channels", label: "Все каналы", variant: "outline" },
  {
    id: "sync",
    label: start.pending.value
      ? "Запускаем…"
      : active.value
        ? "Синхронизация…"
        : "Синхронизировать",
    variant: "default",
    mobileOrder: 1,
    disabled: start.pending.value || active.value || syncDisabled.value,
  },
]);
const description = computed(() => {
  const total = publications.data.value?.total;
  if (total !== undefined)
    return (state.filters.value.search ? "Найдено: " : "Публикаций: ") + total;
  return publications.isPending.value
    ? "Загружаем публикации…"
    : "Количество публикаций недоступно";
});
const scrollKey = computed(() =>
  JSON.stringify([scope.value, id.value, state.filters.value]),
);
const error = computed(() =>
  publications.error.value
    ? channelErrorMessage(publications.error.value)
    : channel.error.value
      ? channelErrorMessage(channel.error.value)
      : "",
);
const syncError = computed(
  () =>
    start.error.value ||
    (sync.error.value
      ? channelErrorMessage(sync.error.value)
      : sync.data.value?.errorCode
        ? channelErrorMessage(sync.data.value.errorCode)
        : ""),
);
watch(
  () => channel.data.value?.verification.status,
  (status) => {
    if (status === "verified") void sync.refetch();
  },
);
watch(
  () => sync.data.value?.status,
  (status, before) => {
    if (status && status !== before && !["queued", "running"].includes(status))
      void client.invalidateQueries({
        queryKey: publicationKeys.root(scope.value, id.value),
      });
  },
);
function open(publicationId: string): void {
  void router.push({
    name: "channel-publication",
    params: { id: id.value, publicationId },
    query: route.query,
  });
}
function changeTab(value: "settings" | "publications"): void {
  if (value === "settings")
    void router.push({
      name: "channel-detail",
      params: { id: id.value },
      query: route.query,
    });
}
function action(value: string): void {
  if (value === "channels") void router.push("/channels");
  else if (value === "sync") void start.execute(id.value);
}
</script>
<template>
  <div
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-4"
    data-slot="channel-publications-page"
  >
    <div class="flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto">
      <ChannelHeader
        class="shrink-0"
        :title="channel.data.value?.name ?? 'Канал'"
        :description="description"
        active-tab="publications"
        :actions="actions"
        @tab="changeTab"
        @action="action"
      />
      <PublicationSyncStatus
        :run="sync.data.value ?? null"
        :loading="sync.isPending.value"
        :disabled="syncDisabled"
        :error="syncError"
      />
      <PublicationsToolbar
        show-bindings
        :binding="state.filters.value.binding"
        @binding="state.setBinding"
        :search="state.filters.value.search"
        :locale="publications.data.value?.locale ?? state.filters.value.locale"
        :locales="publications.data.value?.locales ?? []"
        @search="state.setSearch"
        @locale="state.setLocale"
      />
      <PublicationsBody
        :items="publications.data.value?.items ?? []"
        :pending="publications.isPending.value"
        :error="error"
        :scroll-key="scrollKey"
        :creation="creationState"
        @create="createCatalog"
        @open-catalog="openCatalog"
        @retry="
          publications.refetch();
          channel.refetch();
        "
        @open="open"
      />
    </div>
    <PublicationsFooter
      :offset="state.filters.value.offset"
      :limit="state.filters.value.limit"
      :total="publications.data.value?.total"
      :pending="publications.isPending.value"
      @change="state.setPagination"
    />
  </div>
</template>
