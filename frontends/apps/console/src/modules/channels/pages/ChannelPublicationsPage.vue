<script setup lang="ts">
import { computed, watch, ref, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "vue-sonner";
import { usePublicationCatalogCreation } from "../model/use-publication-catalog-creation";
import {
  publicationLinkQuery,
  publicationListQuery,
} from "../model/publication-navigation";
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
import PublicationsFooter from "../ui/PublicationsFooter.vue";
import UnlinkPublicationDialog from "../ui/UnlinkPublicationDialog.vue";
import { useCatalogBinding } from "../model/bindings/binding.queries";
import { useDeleteCatalogBinding } from "../model/bindings/use-delete-catalog-binding";
import { bindingError } from "../model/bindings/binding.errors";
const route = useRoute(),
  router = useRouter(),
  client = useQueryClient(),
  scope = useChannelScope();
const id = computed(() => String(route.params.id ?? ""));
const deleting = ref<{
  publicationId: string;
  bindingId: string;
  title: string;
} | null>(null);
const unlinkError = ref("");
const remove = useDeleteCatalogBinding();
let mounted = true;
onBeforeUnmount(() => {
  mounted = false;
});
const context = computed(() => JSON.stringify([scope.value, id.value]));
const creation = usePublicationCatalogCreation(id, context);
onBeforeRouteLeave(() => !creation.pending.value);
onBeforeRouteUpdate(
  (to, from) => to.path === from.path || !creation.pending.value,
);
watch(context, () => {
  deleting.value = null;
  unlinkError.value = "";
});
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
const selectedBinding = useCatalogBinding(
  computed(() => (deleting.value ? id.value : "")),
  computed(() => deleting.value?.bindingId ?? ""),
  computed(() => publications.data.value?.locale || state.filters.value.locale),
);
const dialogError = computed(
  () =>
    unlinkError.value ||
    (selectedBinding.error.value
      ? bindingError(selectedBinding.error.value)
      : ""),
);
function requestUnlink(publicationId: string, bindingId: string): void {
  if (remove.isPending.value) return;
  const card = publications.data.value?.items.find(
    (p) => p.id === publicationId,
  );
  const binding = card?.bindings.find((b) => b.id === bindingId);
  if (!binding) return;
  unlinkError.value = "";
  deleting.value = {
    publicationId,
    bindingId,
    title: binding.catalogTitle ?? card?.title ?? "Товар без названия",
  };
}
async function reloadBinding(): Promise<void> {
  unlinkError.value = "";
  await selectedBinding.refetch();
}
async function unlink(): Promise<void> {
  const target = deleting.value,
    group = selectedBinding.data.value;
  if (
    !target ||
    !group ||
    group.id !== target.bindingId ||
    selectedBinding.isFetching.value ||
    selectedBinding.isError.value ||
    remove.isPending.value
  )
    return;
  const captured = context.value;
  const relevant = () =>
    mounted &&
    context.value === captured &&
    deleting.value?.bindingId === target.bindingId;
  unlinkError.value = "";
  try {
    await remove.mutateAsync({
      channelId: id.value,
      id: group.id,
      revision: group.revision,
    });
    if (relevant()) deleting.value = null;
  } catch (cause) {
    if (relevant()) {
      unlinkError.value = bindingError(cause);
      await selectedBinding.refetch();
    }
  }
}
const syncDisabled = computed(
  () => !channel.data.value?.availableCapabilities.includes("publications"),
);
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
    query: publicationListQuery(route.query),
    hash: route.hash,
  });
}
function connect(publicationId: string): void {
  if (creation.pending.value || remove.isPending.value) return;
  void router.push({
    name: "channel-publication",
    params: { id: id.value, publicationId },
    query: publicationLinkQuery(route.query, id.value),
    hash: route.hash,
  });
}
async function createCatalog(publicationId: string): Promise<void> {
  const card = publications.data.value?.items.find(
    (item) => item.id === publicationId,
  );
  if (!card || card.bindings.length || remove.isPending.value) return;
  const captured = context.value;
  const result = await creation.create(card.id);
  if (!result) return;
  toast.success(
    result.created
      ? "Товар создан и связан с публикацией"
      : "Публикация уже связана с товаром",
    {
      description: result.warnings.join(" "),
      action: {
        label: "Открыть товар",
        onClick: () => {
          if (mounted && context.value === captured)
            openCatalog(result.catalogItemId);
        },
      },
    },
  );
}
</script>
<template>
  <div
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-4"
    data-slot="channel-publications-page"
  >
    <div class="flex min-h-0 min-w-0 flex-1 flex-col gap-4">
      <header
        class="flex shrink-0 flex-wrap items-center justify-between gap-3"
      >
        <p class="text-sm text-muted-foreground">{{ description }}</p>
        <Button
          :disabled="start.pending.value || active || syncDisabled"
          @click="start.execute(id)"
          >{{
            start.pending.value
              ? "Запускаем…"
              : active
                ? "Синхронизация…"
                : "Синхронизировать"
          }}</Button
        >
      </header>
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
      <Alert
        v-if="
          creation.pending.value ||
          creation.error.value ||
          creation.warnings.value.length
        "
        :variant="creation.error.value ? 'destructive' : 'default'"
        class="shrink-0"
        ><AlertDescription>
          <p v-if="creation.pending.value" role="status">
            Создаём товар и связь…
          </p>
          <p v-if="creation.error.value">{{ creation.error.value }}</p>
          <p v-for="warning in creation.warnings.value" :key="warning">
            {{ warning }}
          </p>
        </AlertDescription></Alert
      >
      <PublicationsBody
        :items="publications.data.value?.items ?? []"
        :pending="publications.isPending.value"
        :error="error"
        :scroll-key="scrollKey"
        :busy="remove.isPending.value || creation.pending.value"
        @connect="connect"
        @create="createCatalog"
        :out-of-range="state.filters.value.offset > 0"
        @first-page="
          state.setPagination({ page: 1, limit: state.filters.value.limit })
        "
        @unlink="requestUnlink"
        @open-catalog="openCatalog"
        @retry="
          publications.refetch();
          channel.refetch();
        "
        @open="open"
      />
    </div>
    <UnlinkPublicationDialog
      :open="!!deleting"
      :title="deleting?.title ?? ''"
      :loading="selectedBinding.isFetching.value"
      :busy="remove.isPending.value"
      :error="dialogError"
      :can-confirm="
        !!selectedBinding.data.value && !selectedBinding.isError.value
      "
      @close="deleting = null"
      @confirm="unlink"
      @retry="reloadBinding"
    />
    <PublicationsFooter
      :offset="state.filters.value.offset"
      :limit="state.filters.value.limit"
      :total="publications.data.value?.total"
      :pending="publications.isPending.value"
      @change="state.setPagination"
    />
  </div>
</template>
