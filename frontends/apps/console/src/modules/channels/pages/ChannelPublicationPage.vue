<script setup lang="ts">
import { computed } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { toast } from "vue-sonner";
import { Link2, List } from "@lucide/vue";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useChannel } from "../model/channel.queries";
import { usePublication } from "../model/publication.queries";
import { usePublicationsPageState } from "../model/use-publications-page-state";
import { channelErrorMessage } from "../model/channel.errors";
import { bindingPublicationPositions } from "../model/bindings/binding.matching";
import { useChannelScope } from "../model/use-channel-scope";
import { usePublicationCatalogCreation } from "../model/use-publication-catalog-creation";
import { usePublicationDetailsPageState } from "../model/use-publication-details-page-state";
import { channelListReturnTo } from "../model/channel-navigation";
import {
  publicationListQuery,
  publicationLinkQuery,
} from "../model/publication-navigation";
import PublicationHeader from "../ui/PublicationHeader.vue";
import PublicationProperties from "../ui/PublicationProperties.vue";
import PublicationDetailsBody from "../ui/PublicationDetailsBody.vue";
import PublicationCatalogAction from "../ui/PublicationCatalogAction.vue";
import CatalogBindingsPage from "./CatalogBindingsPage.vue";
import "../ui/channel-workspace.css";

const route = useRoute(),
  router = useRouter(),
  scope = useChannelScope();
const id = computed(() => String(route.params.id ?? "")),
  publicationId = computed(() => String(route.params.publicationId ?? ""));
const channel = useChannel(id),
  state = usePublicationsPageState(channel.data),
  page = usePublicationDetailsPageState();
const locale = computed(() => state.filters.value.locale);
const publication = usePublication(id, publicationId, locale);
const creationContext = computed(() =>
  JSON.stringify([scope.value, id.value, publicationId.value]),
);
const creation = usePublicationCatalogCreation(id, creationContext);
const catalogTargets = computed(() => [
  ...new Map(
    (publication.data.value?.card.bindings ?? []).map((binding) => [
      binding.catalogRootId,
      {
        id: binding.catalogRootId,
        label: binding.catalogTitle ?? "Товар без названия",
      },
    ]),
  ).values(),
]);
const loadError = computed(() =>
  publication.error.value || channel.error.value
    ? channelErrorMessage(publication.error.value ?? channel.error.value)
    : "",
);
onBeforeRouteLeave(() => !creation.pending.value);
onBeforeRouteUpdate(
  (to, from) => to.path === from.path || !creation.pending.value,
);
function back(): void {
  void router.push({
    name: "channel-detail",
    params: { id: id.value },
    query: publicationListQuery(route.query),
    hash: route.hash,
  });
}
function openCatalog(itemId: string): void {
  void router.push({
    path: `/catalog/items/${encodeURIComponent(itemId)}`,
    query: {
      locale: publication.data.value?.locale || locale.value || undefined,
    },
  });
}
function connect(): void {
  if (
    creation.pending.value ||
    !publication.data.value ||
    publication.data.value.card.bindings.length
  )
    return;
  void router.replace({
    query: publicationLinkQuery(route.query, id.value),
    hash: route.hash,
  });
}
async function createCatalog(): Promise<void> {
  const card = publication.data.value?.card;
  if (!card || card.bindings.length || publication.isError.value) return;
  const captured = creationContext.value;
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
          if (creationContext.value === captured)
            openCatalog(result.catalogItemId);
        },
      },
    },
  );
}
function retry(): void {
  void publication.refetch();
  void channel.refetch();
}
</script>
<template>
  <div
    class="channel-workspace -mx-4 -mb-4 min-h-0 min-w-0 flex-1 overflow-y-auto bg-background lg:overflow-hidden"
    data-slot="publication-workspace"
  >
    <Teleport to="#workspace-page-header" defer
      ><PublicationHeader
        :title="publication.data.value?.card.title ?? 'Публикация'"
        :channel-name="channel.data.value?.name ?? 'Подключение'"
        :busy="creation.pending.value"
        @channels="router.push(channelListReturnTo(route.query.returnTo))"
        @publications="back"
    /></Teleport>
    <aside class="channel-workspace-fields" aria-label="Сведения о публикации">
      <PublicationProperties
        v-if="publication.data.value"
        :key="creationContext"
        :card="publication.data.value.card"
        :channel="channel.data.value"
        :locale="publication.data.value.locale"
        :locales="publication.data.value.locales"
        :busy="creation.pending.value"
        @locale="state.setLocale"
        @channel="back"
      >
        <template #catalog
          ><PublicationCatalogAction
            :catalog-item-id="catalogTargets[0]?.id ?? null"
            :catalog-targets="catalogTargets"
            :pending="creation.pending.value"
            :disabled="!!loadError"
            :error="creation.error.value"
            :warnings="creation.warnings.value"
            @create="createCatalog"
            @connect="connect"
            @manage="page.selectTab('bindings')"
            @open="openCatalog"
        /></template>
      </PublicationProperties>
      <div v-else class="p-4">
        <Skeleton v-if="publication.isPending.value" class="h-96 w-full" />
        <p v-else class="text-sm text-muted-foreground">
          Сведения о публикации недоступны.
        </p>
      </div>
    </aside>
    <Tabs
      :model-value="page.tab.value"
      class="channel-workspace-publications flex min-w-0 flex-col gap-0"
      @update:model-value="page.selectTab"
    >
      <TabsList
        variant="line"
        aria-label="Разделы публикации"
        class="shrink-0 border-b px-4"
        ><TabsTrigger
          value="positions"
          variant="line"
          :disabled="creation.pending.value"
          ><List class="mr-2 size-4" aria-hidden="true" />Позиции</TabsTrigger
        ><TabsTrigger
          value="bindings"
          variant="line"
          :disabled="creation.pending.value"
          ><Link2 class="mr-2 size-4" aria-hidden="true" />Связи с
          каталогом</TabsTrigger
        ></TabsList
      >
      <TabsContent
        value="positions"
        class="flex min-h-0 flex-1 flex-col p-4 lg:p-6"
        ><PublicationDetailsBody
          :card="publication.data.value?.card"
          :pending="publication.isPending.value"
          :error="loadError"
          :requested-publication-id="publicationId"
          @retry="retry"
      /></TabsContent>
      <TabsContent
        value="bindings"
        class="flex min-h-0 flex-1 flex-col p-4 lg:p-6"
      >
        <CatalogBindingsPage
          v-if="publication.data.value"
          :key="`${scope.join(':')}:${id}:${publication.data.value.card.id}`"
          embedded
          :external-busy="creation.pending.value"
          :channel-id="id"
          :publication-id="publication.data.value.card.id"
          :initial-publications="
            bindingPublicationPositions(publication.data.value.card)
          "
          :publication-has-variants="
            publication.data.value.card.rootKind === 'variable' ||
            publication.data.value.card.items.some(
              (item) => item.kind === 'variant',
            )
          "
          :locale="publication.data.value.locale"
        />
        <PublicationDetailsBody
          v-else
          :card="undefined"
          :pending="publication.isPending.value"
          :error="loadError"
          :requested-publication-id="publicationId"
          @retry="retry"
        />
      </TabsContent>
    </Tabs>
  </div>
</template>
