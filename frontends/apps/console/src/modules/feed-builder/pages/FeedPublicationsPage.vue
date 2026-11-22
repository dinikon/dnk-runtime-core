<script setup lang="ts">
import { computed, ref, watch, nextTick } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { OffsetPagination } from "@/shared/pagination";
import FeedHeader from "../ui/page/FeedHeader.vue";
import FeedSections from "../ui/page/FeedSections.vue";
import AddPublicationsDialog from "../ui/forms/AddPublicationsDialog.vue";
import PublicationsToolbar from "../ui/page/PublicationsToolbar.vue";
import PublicationsList from "../ui/results/PublicationsList.vue";
import PublicationPricePreview from "../ui/results/PublicationPricePreview.vue";
import {
  usePublications,
  usePublication,
  usePublicationProducts,
  usePublicationVariants,
} from "../model/feed-publication.queries";
import { usePublicationsPageState } from "../model/use-publications-page-state";
import { usePublicationSelection } from "../model/use-publication-selection";
import { usePublicationVariantSelection } from "../model/use-publication-variant-selection";
import { useAddPublications } from "../model/use-add-publications";
import { useChangePublication } from "../model/use-change-publication";
import { useArchivePublication } from "../model/use-archive-publication";
import { useRestorePublication } from "../model/use-restore-publication";
import { useFeedScope } from "../model/use-feed-scope";
import { useFeed } from "../model/feed.queries";
import { useFeedSchema, useSchemaMetadata } from "../model/feed-schema.queries";
import { useFeedCalculationPreview } from "../model/use-feed-calculation-preview";
import { fieldDraft, fieldIsReadonly } from "../model/feed-schema.draft";
import { calculationErrorMessage } from "../model/feed-calculation.errors";
import {
  publicationErrorMessage,
  publicationStatusLabel,
} from "../model/feed-publication.errors";
import { publicationKeys } from "../model/feed-publication.query-keys";
import { feedListReturnTo } from "../model/feed.navigation";
import type {
  Publication,
  PublicationPage,
} from "../model/feed-publication.types";
const route = useRoute(),
  router = useRouter(),
  scope = useFeedScope(),
  cache = useQueryClient();
const id = computed(() => String(route.params.id ?? "")),
  state = usePublicationsPageState(),
  locale = computed(() => state.filters.value.locale);
const query = usePublications(id, state.filters),
  feed = useFeed(id),
  schema = useFeedSchema(id),
  metadata = useSchemaMetadata();
const selectedId = computed(() =>
  typeof route.query.publication === "string" ? route.query.publication : "",
);
const detailQuery = usePublication(selectedId, locale);
const data = computed(() => {
  void query.data.value;
  return cache.getQueryData<PublicationPage>(
    publicationKeys.list(scope.value, id.value, state.filters.value),
  );
});
const detailRecord = computed(() => {
  void detailQuery.data.value;
  return cache.getQueryData<Publication>(
    publicationKeys.detail(scope.value, selectedId.value, locale.value),
  );
});
const detail = computed(() =>
  detailRecord.value?.feedId === id.value ? detailRecord.value : undefined,
);
const detailError = computed(() =>
  detailQuery.error.value
    ? publicationErrorMessage(detailQuery.error.value)
    : detailRecord.value && detailRecord.value.feedId !== id.value
      ? "Публикация не принадлежит текущему фиду."
      : "",
);
const add = useAddPublications(),
  change = useChangePublication(),
  archive = useArchivePublication(),
  restore = useRestorePublication();
const selection = usePublicationSelection(),
  dialog = ref(false),
  baseVersion = ref<number | null>(null),
  fieldId = ref("");
const busy = computed(
  () =>
    add.pending.value ||
    change.pending.value ||
    archive.pending.value ||
    restore.pending.value,
);
const readonly = computed(
  () =>
    data.value?.feedStatus === "ARCHIVED" ||
    feed.data.value?.status === "ARCHIVED",
);
const conflict = computed(
  () =>
    dialog.value &&
    baseVersion.value !== null &&
    data.value !== undefined &&
    baseVersion.value !== data.value.feedVersion,
);
const products = usePublicationProducts(
  locale,
  selection.search,
  selection.offset,
  dialog,
);
const variants = usePublicationVariants(
  selection.rootId,
  locale,
  selection.variantOffset,
  dialog,
);
const context = computed(() => JSON.stringify([scope.value, id.value]));
const selectionEpoch = ref(0);
watch(
  () =>
    JSON.stringify([
      context.value,
      dialog.value,
      baseVersion.value,
      selection.rootId.value,
      locale.value,
    ]),
  () => {
    selectionEpoch.value++;
  },
  { flush: "sync" },
);
const all = usePublicationVariantSelection(
  id,
  selection.rootId,
  locale,
  computed(() =>
    JSON.stringify([context.value, dialog.value, baseVersion.value]),
  ),
);
const archivedExistingCount = ref(0),
  pausedExistingCount = ref(0);
const moneyFields = computed(
  () =>
    schema.data.value?.definition.fields.filter(
      (f) => f.typeDefinition.kind === "money",
    ) ?? [],
);
const priceField = computed(() => {
  const field = moneyFields.value.find((f) => f.id === fieldId.value);
  return field ? fieldDraft(field) : undefined;
});
const priceBlocked = computed(
  () =>
    readonly.value ||
    busy.value ||
    !detail.value ||
    !detail.value.sourceAvailable ||
    (!!priceField.value && fieldIsReadonly(priceField.value)),
);
const price = useFeedCalculationPreview(
  id,
  computed(() => schema.data.value?.version ?? null),
  priceField,
  metadata.data,
  priceBlocked,
  computed(() => false),
);
watch(
  [detail, context],
  () => {
    price.root.value = null;
    price.variant.value = null;
    const d = detail.value;
    if (!d) return;
    price.root.value = {
      id: d.itemId,
      title: d.parentTitle ?? d.title ?? d.itemId,
      sku: d.variantId ? null : d.sku,
      kind: d.variantId ? "variable" : "simple",
    };
    if (d.variantId)
      price.variant.value = {
        id: d.variantId,
        title: d.title ?? d.sku ?? d.variantId,
        sku: d.sku,
        kind: "variant",
      };
  },
  { immediate: true, flush: "sync" },
);
watch(selectedId, async (value) => {
  if (!value) return;
  const stamp = context.value;
  await nextTick();
  if (stamp !== context.value || selectedId.value !== value) return;
  document
    .querySelector<HTMLElement>('[aria-label="Карточка публикации"]')
    ?.scrollIntoView({ block: "start", behavior: "smooth" });
});
watch(
  moneyFields,
  (fields) => {
    if (!fields.some((f) => f.id === fieldId.value))
      fieldId.value = fields[0]?.id ?? "";
  },
  { immediate: true },
);
watch(
  context,
  () => {
    dialog.value = false;
    selection.reset();
    baseVersion.value = null;
    fieldId.value = "";
    archivedExistingCount.value = 0;
    pausedExistingCount.value = 0;
  },
  { flush: "sync" },
);
watch(data, (value) => {
  if (
    value &&
    state.filters.value.offset > 0 &&
    state.filters.value.offset >= value.total
  )
    state.setOffset(Math.max(0, Math.ceil(value.total / 25) - 1) * 25);
});
onBeforeRouteLeave(
  () =>
    !busy.value &&
    (!selection.selected.value.length ||
      !dialog.value ||
      window.confirm("Закрыть выбор товаров без добавления?")),
);
onBeforeRouteUpdate(() => !busy.value);
const error = computed(() =>
  publicationErrorMessage(
    change.error.value || archive.error.value || restore.error.value,
  ),
);
const dialogError = computed(
  () =>
    selection.error.value ||
    publicationErrorMessage(add.error.value || all.error.value),
);
function sections(section: "settings" | "schema" | "publications"): void {
  if (section === "publications") return;
  void router.push({
    name: section === "settings" ? "feed-detail" : "feed-schema",
    params: { id: id.value },
    query: { returnTo: feedListReturnTo(route.query.returnTo) },
  });
}
function open(item: Publication): void {
  void router.replace({ query: { ...route.query, publication: item.id } });
}
function closeDetail(): void {
  void router.replace({ query: { ...route.query, publication: undefined } });
}
function clearActionErrors(): void {
  change.error.value = undefined;
  archive.error.value = undefined;
  restore.error.value = undefined;
}
function showArchived(): void {
  void router.replace({
    query: {
      ...route.query,
      status: "ARCHIVED",
      search: undefined,
      offset: undefined,
      publication: undefined,
    },
  });
}
function openAdd(): void {
  if (readonly.value || busy.value || !data.value) return;
  selection.reset();
  add.error.value = undefined;
  baseVersion.value = data.value.feedVersion;
  dialog.value = true;
}
function dialogOpen(value: boolean): void {
  if (busy.value) return;
  dialog.value = value;
  if (!value) selection.reset();
}
async function refresh(): Promise<void> {
  const stamp = context.value;
  const result = await query.refetch();
  if (stamp !== context.value) return;
  if (result.data && !result.isError) {
    baseVersion.value = result.data.feedVersion;
    add.error.value = undefined;
  }
  void schema.refetch();
}
async function addSelected(): Promise<void> {
  if (
    baseVersion.value === null ||
    conflict.value ||
    readonly.value ||
    !dialog.value ||
    !selection.selected.value.length
  )
    return;
  const stamp = context.value;
  const result = await add.execute({
    feedId: id.value,
    expectedFeedVersion: baseVersion.value,
    references: selection.selected.value.map(({ itemId, variantId }) => ({
      itemId,
      variantId,
    })),
  });
  if (stamp !== context.value || !result) return;
  const created = result.value.items.filter(
    (i) => i.outcome === "CREATED",
  ).length;
  archivedExistingCount.value = result.value.items.filter(
    (i) => i.outcome === "EXISTING" && i.status === "ARCHIVED",
  ).length;
  pausedExistingCount.value = result.value.items.filter(
    (i) => i.outcome === "EXISTING" && i.status === "PAUSED",
  ).length;
  toast.success(
    `Добавлено: ${created}. Уже в составе: ${result.value.items.length - created}.`,
  );
  dialog.value = false;
  selection.reset();
  await query.refetch();
}
async function allVariants(): Promise<void> {
  const epoch = selectionEpoch.value;
  const values = await all.execute();
  if (values && epoch === selectionEpoch.value) selection.merge(values);
}
async function changeStatus(
  item: Publication,
  status: "ENABLED" | "PAUSED",
): Promise<void> {
  if (readonly.value || busy.value) return;
  clearActionErrors();
  const result = await change.execute({
    id: item.id,
    expectedVersion: item.version,
    status,
  });
  if (result) {
    await query.refetch();
    if (selectedId.value) await detailQuery.refetch();
  }
}
async function remove(item: Publication): Promise<void> {
  if (
    readonly.value ||
    busy.value ||
    !window.confirm(
      `Убрать «${item.title ?? item.sku ?? "позицию"}» из фида? Привязка сохранится в архиве.`,
    )
  )
    return;
  clearActionErrors();
  const result = await archive.execute({
    id: item.id,
    expectedVersion: item.version,
  });
  if (result) {
    await query.refetch();
    if (selectedId.value) await detailQuery.refetch();
  }
}
async function reinstate(item: Publication): Promise<void> {
  if (
    readonly.value ||
    busy.value ||
    !window.confirm("Вернуть эту позицию в фид?")
  )
    return;
  clearActionErrors();
  const result = await restore.execute({
    id: item.id,
    expectedVersion: item.version,
  });
  if (result) {
    await query.refetch();
    if (selectedId.value) await detailQuery.refetch();
  }
}
function retrySources(): void {
  void products.refetch();
  if (selection.rootId.value) void variants.refetch();
}
</script>
<template>
  <Teleport to="#workspace-page-header" defer
    ><FeedHeader
      :title="feed.data.value?.name ?? 'Товары фида'"
      :archivable="false"
      :busy="busy"
      @back="router.push(feedListReturnTo(route.query.returnTo))"
  /></Teleport>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Товары фида</h1>
        <p class="text-sm text-muted-foreground">
          Участвуют: {{ data?.counts.ENABLED ?? 0 }} · Приостановлены:
          {{ data?.counts.PAUSED ?? 0 }} · В архиве:
          {{ data?.counts.ARCHIVED ?? 0 }}
        </p>
      </div>
      <Button
        type="button"
        :disabled="readonly || busy || !data"
        @click="openAdd"
        >Добавить товары</Button
      >
    </header>
    <FeedSections
      current="publications"
      :disabled="busy"
      @navigate="sections"
    />
    <Alert v-if="readonly"
      ><AlertDescription
        >Фид находится в архиве. Состав доступен только для
        просмотра.</AlertDescription
      ></Alert
    >
    <Alert v-if="query.error.value" variant="destructive"
      ><AlertDescription class="flex flex-wrap gap-2"
        >{{ publicationErrorMessage(query.error.value)
        }}<Button
          type="button"
          variant="outline"
          :disabled="query.isFetching.value"
          @click="query.refetch()"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <Alert v-if="archivedExistingCount || pausedExistingCount"
      ><AlertDescription class="flex flex-wrap items-center gap-2"
        >Повторно выбраны позиции: {{ pausedExistingCount }} приостановленных,
        {{ archivedExistingCount }} архивных. Их участие сохранено.<Button
          v-if="archivedExistingCount"
          type="button"
          variant="outline"
          @click="showArchived"
          >Открыть архив для восстановления</Button
        ></AlertDescription
      ></Alert
    >
    <Alert v-if="error" variant="destructive"
      ><AlertDescription>{{ error }}</AlertDescription></Alert
    >
    <PublicationsToolbar
      :filters="state.filters.value"
      :locales="metadata.data.value?.locales ?? []"
      :disabled="busy"
      @search="state.setSearch"
      @status="state.setStatus"
      @locale="state.setLocale"
    />
    <div
      v-if="!data && !query.error.value"
      role="status"
      aria-label="Загрузка состава"
      class="flex flex-col gap-3"
    >
      <Skeleton v-for="i in 4" :key="i" class="h-24 w-full" />
    </div>
    <template v-if="data"
      ><p
        v-if="!data.items.length"
        class="rounded-lg border p-6 text-muted-foreground"
      >
        {{
          state.filters.value.search || state.filters.value.status
            ? "Позиции не найдены. Измените фильтры."
            : "В фиде пока нет товаров. Добавьте товары и выбранные варианты из каталога."
        }}
      </p>
      <PublicationsList
        v-else
        :items="data.items"
        :busy="busy"
        :readonly="readonly"
        :selected-id="selectedId"
        @open="open"
        @pause="changeStatus($event, 'PAUSED')"
        @enable="changeStatus($event, 'ENABLED')"
        @archive="remove"
        @restore="reinstate" /><OffsetPagination
        :total="data.total"
        :page="Math.floor(state.filters.value.offset / 25) + 1"
        :limit-options="[25]"
        locale="ru"
        :limit="state.filters.value.limit"
        :disabled="query.isFetching.value || busy"
        @change="state.setOffset(($event.page - 1) * 25)"
    /></template>
    <section
      v-if="selectedId"
      class="flex min-w-0 flex-col gap-4 rounded-lg border p-4"
      aria-label="Карточка публикации"
    >
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="text-lg font-semibold">
          {{ detail?.title ?? detail?.sku ?? "Публикация" }}
        </h2>
        <Button type="button" variant="outline" @click="closeDetail"
          >Закрыть карточку</Button
        >
      </div>
      <Alert v-if="detailError" variant="destructive"
        ><AlertDescription class="flex flex-col items-start gap-2"
          ><p>{{ detailError }}</p>
          <Button
            v-if="detailQuery.error.value"
            type="button"
            variant="outline"
            @click="detailQuery.refetch()"
            >Повторить</Button
          ></AlertDescription
        ></Alert
      >
      <p v-else-if="!detail" role="status">Загрузка публикации…</p>
      <template v-if="detail"
        ><p class="break-all text-sm text-muted-foreground">
          {{ detail.sku ?? "Без SKU" }} ·
          {{ publicationStatusLabel(detail.status) }}
        </p>
        <p v-if="detail.parentTitle" class="text-sm">
          Карточка: {{ detail.parentTitle }}
        </p>
        <p v-if="!detail.sourceAvailable" class="text-sm text-destructive">
          Позиция Catalog недоступна. Привязка сохранена.
        </p>
        <PublicationPricePreview
          :fields="
            moneyFields.map((f) => ({
              id: f.id,
              label: f.label,
              manual:
                f.typeDefinition.kind === 'money' &&
                f.typeDefinition.value.mode === 'MANUAL',
            }))
          "
          :field-id="fieldId"
          :result="price.result.value"
          :stale="price.stale.value"
          :pending="price.pending.value"
          :error="calculationErrorMessage(price.error.value)"
          :disabled="!price.canPreview.value"
          :manual="
            priceField?.typeDefinition.kind === 'money' &&
            priceField.typeDefinition.value.mode === 'MANUAL'
          "
          @field="fieldId = $event"
          @preview="price.preview"
      /></template>
    </section>
    <AddPublicationsDialog
      :open="dialog"
      :products="products.data.value?.items ?? []"
      :total="products.data.value?.total ?? 0"
      :variants="variants.data.value?.items ?? []"
      :variants-total="variants.data.value?.total ?? 0"
      :selected="selection.selected.value"
      :search="selection.search.value"
      :offset="selection.offset.value"
      :variant-offset="selection.variantOffset.value"
      :root-id="selection.rootId.value"
      :loading="products.isFetching.value"
      :variants-loading="variants.isFetching.value"
      :pending="add.pending.value"
      :all-pending="all.pending.value"
      :error="dialogError"
      :source-error="
        products.error.value || (selection.rootId.value && variants.error.value)
          ? 'Не удалось загрузить Catalog. Повторите загрузку.'
          : ''
      "
      :conflict="conflict"
      :readonly="readonly"
      @open="dialogOpen"
      @search="selection.search.value = $event"
      @offset="selection.offset.value = $event"
      @variant-offset="selection.variantOffset.value = $event"
      @root="selection.rootId.value = $event"
      @toggle="selection.toggle"
      @remove="selection.remove"
      @all="allVariants"
      @submit="addSelected"
      @refresh="refresh"
      @retry="retrySources"
    />
  </div>
</template>
