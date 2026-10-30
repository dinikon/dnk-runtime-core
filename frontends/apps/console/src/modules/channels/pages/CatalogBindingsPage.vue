<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { useBindingStock } from "../model/stock.queries";
import { useRefreshPublicationStock } from "../model/use-refresh-publication-stock";
import { useExportCatalogStock } from "../model/use-export-catalog-stock";
import { stockErrorMessage } from "../model/stock.errors";
import { bindingKeys } from "../model/bindings/binding.query-keys";
import { publicationKeys } from "../model/publication.query-keys";
import BindingStockPanel from "../ui/bindings/BindingStockPanel.vue";
import { useRouter, onBeforeRouteLeave, onBeforeRouteUpdate } from "vue-router";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";
import OffsetPagination from "@/shared/pagination/OffsetPagination.vue";
import BindingCandidates from "../ui/bindings/BindingCandidates.vue";
import BindingGroupsBody from "../ui/bindings/BindingGroupsBody.vue";
import BindingPairsForm from "../ui/bindings/BindingPairsForm.vue";
import { usePublicationSync } from "../model/publication.queries";
import { useChannels, useChannel } from "../model/channel.queries";
import { useChannelScope } from "../model/use-channel-scope";
import {
  useCatalogBindings,
  useCatalogBinding,
  useBindingCandidates,
  useBindingPreview,
} from "../model/bindings/binding.queries";
import { useBindingsPageState } from "../model/bindings/use-bindings-page-state";
import { useCreateCatalogBinding } from "../model/bindings/use-create-catalog-binding";
import { useUpdateCatalogBinding } from "../model/bindings/use-update-catalog-binding";
import { useDeleteCatalogBinding } from "../model/bindings/use-delete-catalog-binding";
import {
  bindingError,
  bindingCreationUncertain,
  bindingIssueLabels,
} from "../model/bindings/binding.errors";
import { suggestBindingPairs } from "../model/bindings/binding.matching";
import {
  bindingModes,
  bindingStates,
  type BindingMode,
  type BindingPair,
  type BindingPosition,
  type BindingProposal,
  type CatalogBinding,
} from "../model/bindings/binding.types";
const props = defineProps<{
  catalogRootId?: string;
  catalogKind?: string;
  channelId?: string;
  publicationId?: string;
  initialPublications?: BindingPosition[];
  publicationHasVariants?: boolean;
  locale: string;
  embedded?: boolean;
  externalBusy?: boolean;
}>();
const router = useRouter(),
  state = useBindingsPageState(),
  scope = useChannelScope();
const stockGroup = ref<CatalogBinding | null>(null),
  stockSelected = ref<string[]>([]),
  stockActionError = ref("");
const stockChannel = computed(() => stockGroup.value?.channelId ?? ""),
  stockGroupId = computed(() => stockGroup.value?.id ?? "");
const stock = useBindingStock(stockChannel, stockGroupId);
const refreshStock = useRefreshPublicationStock(),
  exportStock = useExportCatalogStock();
const stockBusy = computed(
  () => refreshStock.isPending.value || exportStock.isPending.value,
);
const stockCache = useQueryClient();
watch(
  [
    scope,
    () => props.catalogRootId,
    () => props.channelId,
    () => props.publicationId,
  ],
  () => {
    stockGroup.value = null;
    stockSelected.value = [];
    stockActionError.value = "";
  },
);
const seenStockResults = new Set<string>();
watch(
  () => [scope.value, stockChannel.value, stockGroupId.value],
  () => seenStockResults.clear(),
);
watch(
  () => stock.data.value,
  (value) => {
    const terminal =
      value?.items.filter(
        (item) =>
          item.operation &&
          !["queued", "running"].includes(item.operation.status),
      ) ?? [];
    if (terminal.some((item) => !seenStockResults.has(item.operation!.id))) {
      terminal.forEach((item) => seenStockResults.add(item.operation!.id));
      void stockCache.invalidateQueries({
        queryKey: bindingKeys.root(scope.value),
      });
      void stockCache.invalidateQueries({
        queryKey: publicationKeys.root(scope.value, stockChannel.value),
      });
    }
  },
);
function repeatStock(direction: "read" | "write", id: string): void {
  stockSelected.value = [id];
  void stockAction(direction);
}
function openStock(group: CatalogBinding): void {
  stockGroup.value = group;
  stockSelected.value = group.items.map((v) => v.publicationId);
  stockActionError.value = "";
}
async function stockAction(direction: "read" | "write"): Promise<void> {
  if (!stockGroup.value || stockBusy.value || !stockSelected.value.length)
    return;
  const captured = JSON.stringify([
    scope.value,
    stockChannel.value,
    stockGroupId.value,
  ]);
  stockActionError.value = "";
  try {
    const input = {
      channelId: stockChannel.value,
      groupId: stockGroupId.value,
      publicationIds: [...stockSelected.value],
    };
    await (direction === "read"
      ? refreshStock.mutateAsync(input)
      : exportStock.mutateAsync(input));
  } catch (error) {
    if (
      captured ===
      JSON.stringify([scope.value, stockChannel.value, stockGroupId.value])
    )
      stockActionError.value = stockErrorMessage(error);
  }
}
const filters = computed(() => ({
  catalogRootId: props.catalogRootId,
  channelId: props.channelId,
  publicationId: props.publicationId,
  locale: props.locale,
  offset: state.offset.value,
  limit: state.limit.value,
}));
const groups = useCatalogBindings(filters);
const sourceAlreadyBound = computed(
  () => !!props.publicationId && !!groups.data.value?.total,
);
const channelId = computed(() => props.channelId || state.channelId.value);
const channel = useChannel(channelId);
const sync = usePublicationSync(channelId);
const channelOffset = ref(0),
  channelSearch = ref("");
const channelFilters = computed(() => ({
  search: channelSearch.value,
  platformKind: "",
  status: "",
  offset: channelOffset.value,
}));
const channels = useChannels(channelFilters);
const editId = computed(() =>
  state.groupId.value === "new" ? "" : state.groupId.value,
);
const locale = computed(() => props.locale);
const current = useCatalogBinding(channelId, editId, locale);
const catalogId = ref(""),
  publicationRoot = ref<string | null>(null),
  mode = ref<BindingMode>("SIMPLE_TO_SIMPLE"),
  items = ref<BindingPair[]>([]);
const initial = ref(""),
  loadedGroup = ref<CatalogBinding | null>(null),
  writeError = ref(""),
  uncertain = ref(false);
const catalogSearch = ref(""),
  publicationSearch = ref(""),
  catalogOffset = ref(0),
  publicationOffset = ref(0),
  catalogLimit = ref(25),
  publicationLimit = ref(25);
const remembered = ref<BindingPosition[]>([]);
const proposal = computed<BindingProposal>(() => ({
  catalogRootId: catalogId.value,
  mode: mode.value,
  publicationRootId:
    mode.value === "VARIABLE_TO_SIMPLE" ? null : publicationRoot.value,
  items: items.value,
  locale: props.locale,
  ...(editId.value ? { groupId: editId.value } : {}),
}));
const draftKey = computed(() =>
  JSON.stringify({
    catalog: catalogId.value,
    root: publicationRoot.value,
    mode: mode.value,
    items: items.value,
  }),
);
const dirty = computed(
  () => !!state.groupId.value && initial.value !== draftKey.value,
);
const ready = computed(
  () =>
    !!state.groupId.value &&
    !!catalogId.value &&
    !!channelId.value &&
    (mode.value === "VARIABLE_TO_SIMPLE" || !!publicationRoot.value) &&
    (!editId.value || !!loadedGroup.value),
);
const preview = useBindingPreview(channelId, proposal, ready);
const candidateFilters = computed(() => ({
  channelId: channelId.value,
  mode: mode.value,
  locale: props.locale,
  search: catalogSearch.value,
  offset: catalogOffset.value,
  limit: catalogLimit.value,
}));
const publicationFilters = computed(() => ({
  ...candidateFilters.value,
  search: publicationSearch.value,
  offset: publicationOffset.value,
  limit: publicationLimit.value,
}));
const catalogCandidates = useBindingCandidates(
  "catalog",
  candidateFilters,
  computed(() => !!state.groupId.value && !catalogId.value),
);
const publicationCandidates = useBindingCandidates(
  "publication",
  publicationFilters,
  computed(
    () =>
      !!state.groupId.value &&
      !!catalogId.value &&
      (!publicationRoot.value || mode.value === "VARIABLE_TO_SIMPLE"),
  ),
);
const compatibleOffset = ref(0),
  compatibleLimit = ref(25);
const compatibleFilters = computed(() => ({
  catalogRootId:
    props.publicationId &&
    state.groupId.value === "new" &&
    mode.value === "VARIABLE_TO_SIMPLE"
      ? catalogId.value
      : undefined,
  channelId:
    props.publicationId &&
    state.groupId.value === "new" &&
    mode.value === "VARIABLE_TO_SIMPLE" &&
    catalogId.value
      ? channelId.value
      : undefined,
  mode: "VARIABLE_TO_SIMPLE" as const,
  locale: props.locale,
  offset: compatibleOffset.value,
  limit: compatibleLimit.value,
}));
const compatible = useCatalogBindings(compatibleFilters);
watch([catalogId, channelId, mode], () => {
  compatibleOffset.value = 0;
});
const create = useCreateCatalogBinding(),
  update = useUpdateCatalogBinding(),
  remove = useDeleteCatalogBinding();
const busy = computed(
  () =>
    create.isPending.value ||
    update.isPending.value ||
    remove.isPending.value ||
    !!props.externalBusy,
);
const modes = computed<BindingMode[]>(() => {
  if (loadedGroup.value) return [loadedGroup.value.mode];
  if (props.catalogKind === "simple") return ["SIMPLE_TO_SIMPLE"];
  if (props.publicationHasVariants)
    return channel.data.value?.platformKind === "rozetka"
      ? []
      : ["VARIABLE_TO_VARIABLE"];
  if (props.publicationId) return ["SIMPLE_TO_SIMPLE", "VARIABLE_TO_SIMPLE"];
  return channel.data.value?.platformKind === "rozetka"
    ? ["VARIABLE_TO_SIMPLE"]
    : ["VARIABLE_TO_VARIABLE", "VARIABLE_TO_SIMPLE"];
});
const options = computed(() => {
  const values = new Map<string, BindingPosition>();
  for (const p of [
    ...remembered.value,
    ...(publicationCandidates.data.value?.items ?? []),
    ...(preview.data.value?.publications ?? []),
  ])
    values.set(p.id, p);
  return [...values.values()];
});
const occupied = computed(() =>
  (publicationCandidates.data.value?.occupiedIds ?? []).filter(
    (id) => !loadedGroup.value?.items.some((p) => p.publicationId === id),
  ),
);
const allowed = computed(
  () => loadedGroup.value?.items.map((p) => p.publicationId) ?? [],
);
const deleting = ref<CatalogBinding | null>(null);
function initialize(): void {
  loadedGroup.value = null;
  writeError.value = "";
  uncertain.value = false;
  remembered.value = [...(props.initialPublications ?? [])];
  catalogId.value = props.catalogRootId ?? "";
  mode.value = props.publicationHasVariants
    ? "VARIABLE_TO_VARIABLE"
    : props.catalogKind === "variable"
      ? "VARIABLE_TO_SIMPLE"
      : "SIMPLE_TO_SIMPLE";
  publicationRoot.value = props.publicationId ?? null;
  items.value = [];
  catalogSearch.value = "";
  publicationSearch.value = "";
  catalogOffset.value = 0;
  publicationOffset.value = 0;
  initial.value = draftKey.value;
}
watch(
  () => [
    state.groupId.value,
    channelId.value,
    props.catalogRootId,
    props.publicationId,
    props.locale,
  ],
  initialize,
  { immediate: true },
);
function hydrateGroup(v: CatalogBinding): void {
  loadedGroup.value = v;
  catalogId.value = v.catalogRootId;
  mode.value = v.mode;
  publicationRoot.value = v.publicationRootId;
  items.value = v.items.map((p) => ({ ...p }));
  remembered.value = [
    ...(props.initialPublications ?? []),
    ...v.preview.publications,
  ];
  initial.value = draftKey.value;
}
watch(
  current.data,
  (v) => {
    if (v && v.id === editId.value && !loadedGroup.value) hydrateGroup(v);
  },
  { immediate: true },
);
watch(scope, () => {
  initialize();
  deleting.value = null;
  void state.close();
});
watch(catalogSearch, () => {
  catalogOffset.value = 0;
});
watch(publicationSearch, () => {
  publicationOffset.value = 0;
});
const confirmDiscard = ref(false);
let discardDecision: ((value: boolean) => void) | null = null;
function discard(value: boolean): void {
  if (value) initial.value = draftKey.value;
  confirmDiscard.value = false;
  discardDecision?.(value);
  discardDecision = null;
}
async function canClose(): Promise<boolean> {
  if (busy.value) return false;
  if (!dirty.value) return true;
  confirmDiscard.value = true;
  return await new Promise<boolean>((resolve) => {
    discardDecision = resolve;
  });
}
onUnmounted(() => discardDecision?.(false));
async function close(): Promise<void> {
  if (await canClose()) {
    await state.close();
  }
}
onBeforeRouteLeave(canClose);
onBeforeRouteUpdate((to, from) => {
  const contextChanged =
    to.path !== from.path ||
    to.query.binding !== from.query.binding ||
    to.query.tab !== from.query.tab ||
    to.query.publication_tab !== from.query.publication_tab ||
    to.query.locale !== from.query.locale;
  return !contextChanged || canClose();
});
async function open(group?: CatalogBinding): Promise<void> {
  if (!(await canClose())) return;
  initial.value = draftKey.value;
  await state.open(
    group?.id ?? "new",
    group?.channelId ?? props.channelId ?? "",
  );
}
function chooseChannel(id: string): void {
  void state.open("new", id);
}
function changeMode(value: string): void {
  mode.value = value as BindingMode;
  items.value = [];
  publicationRoot.value = props.publicationId ?? null;
  publicationOffset.value = 0;
  catalogOffset.value = 0;
  catalogId.value = props.catalogRootId ?? "";
}
function choosePublication(id: string): void {
  if (mode.value !== "VARIABLE_TO_SIMPLE") {
    publicationRoot.value = id;
    items.value = [];
  } else {
    const value = publicationCandidates.data.value?.items.find(
      (p) => p.id === id,
    );
    if (value && !remembered.value.some((p) => p.id === id))
      remembered.value.push(value);
  }
}
function pair(catalogId: string, publicationId: string): void {
  const p = options.value.find((p) => p.id === publicationId);
  if (p && !remembered.value.some((v) => v.id === p.id))
    remembered.value.push(p);
  items.value = [
    ...items.value.filter((p) => p.catalogId !== catalogId),
    ...(publicationId ? [{ catalogId, publicationId }] : []),
  ];
  writeError.value = "";
}
function suggest(): void {
  items.value = suggestBindingPairs(
    preview.data.value?.catalogPositions ?? [],
    mode.value === "VARIABLE_TO_SIMPLE"
      ? options.value
      : (preview.data.value?.publications ?? []),
    items.value,
    occupied.value,
  );
}
async function save(): Promise<void> {
  const view = preview.data.value;
  if (
    !view ||
    preview.isFetching.value ||
    view.issues.length ||
    !items.value.length ||
    uncertain.value ||
    (!editId.value && sourceAlreadyBound.value)
  )
    return;
  writeError.value = "";
  const context = scope.value.join(":"),
    sent = JSON.stringify(proposal.value);
  try {
    const result = loadedGroup.value
      ? await update.mutateAsync({
          channelId: channelId.value,
          id: loadedGroup.value.id,
          revision: loadedGroup.value.revision,
          proposal: proposal.value,
          preview: view,
        })
      : await create.mutateAsync({
          channelId: channelId.value,
          proposal: proposal.value,
          preview: view,
        });
    if (scope.value.join(":") !== context) return;
    if (JSON.stringify(proposal.value) === sent) initial.value = draftKey.value;
    await state.open(result.id, channelId.value);
    const refreshed = await current.refetch();
    if (scope.value.join(":") !== context || editId.value !== result.id) return;
    if (refreshed.data) {
      if (!dirty.value) hydrateGroup(refreshed.data);
      else loadedGroup.value = refreshed.data;
    }
  } catch (error) {
    if (scope.value.join(":") !== context) return;
    writeError.value = bindingError(error);
    if (!loadedGroup.value && bindingCreationUncertain(error)) {
      uncertain.value = true;
      await groups.refetch();
    } else await preview.refetch();
  }
}
async function reloadGroup(): Promise<void> {
  if (!(await canClose())) return;
  const context = scope.value.join(":"),
    identifier = editId.value;
  const result = await current.refetch();
  if (
    context === scope.value.join(":") &&
    identifier === editId.value &&
    result.data
  ) {
    hydrateGroup(result.data);
    writeError.value = "";
  }
}
async function unlink(): Promise<void> {
  const group = deleting.value;
  if (!group) return;
  const context = scope.value.join(":");
  writeError.value = "";
  try {
    await remove.mutateAsync({
      channelId: group.channelId,
      id: group.id,
      revision: group.revision,
    });
    if (context !== scope.value.join(":")) return;
    deleting.value = null;
    if (state.groupId.value === group.id) {
      initial.value = draftKey.value;
      await state.close();
    }
  } catch (error) {
    if (context === scope.value.join(":"))
      writeError.value = bindingError(error);
  }
}
function goCatalog(id: string): void {
  void router.push({
    path: `/catalog/items/${id}`,
    query: { locale: props.locale, tab: "publications" },
  });
}
function goPublication(group: CatalogBinding): void {
  const publicationId =
    group.publicationRootId ?? group.items[0]?.publicationId;
  if (publicationId)
    void router.push({
      name: "channel-publication",
      params: { id: group.channelId, publicationId },
      query: {
        locale: props.locale,
        binding: group.id,
        binding_channel: group.channelId,
      },
    });
}
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-4"
    aria-label="Связи публикаций с Catalog"
  >
    <div class="flex shrink-0 flex-wrap items-center justify-between gap-3">
      <div v-if="!embedded">
        <h2 class="text-xl font-semibold">
          {{ catalogRootId ? "Публикации" : "Связь с Catalog" }}
        </h2>
        <p class="text-muted-foreground text-sm">
          Связи сопоставляют позиции. Отправка остатков управляется настройкой
          канала.
        </p>
      </div>
      <div class="ml-auto flex gap-2">
        <Button
          variant="outline"
          :disabled="busy || groups.isFetching.value"
          @click="groups.refetch()"
          >Обновить</Button
        ><Button
          :disabled="
            busy ||
            (!!publicationId && (!groups.data.value || sourceAlreadyBound))
          "
          @click="open()"
          >Создать связь</Button
        >
      </div>
    </div>
    <p v-if="sourceAlreadyBound" class="text-muted-foreground text-sm">
      Публикация закреплена за группой. Для привязки к другой карточке сначала
      снимите существующую связь.
    </p>
    <BindingGroupsBody
      :items="groups.data.value?.items ?? []"
      :loading="groups.isPending.value"
      :error="groups.error.value ? bindingError(groups.error.value) : ''"
      :show-catalog="!catalogRootId"
      :out-of-range="state.offset.value > 0"
      :can-create="
        !busy &&
        (!publicationId || (!!groups.data.value && !sourceAlreadyBound))
      "
      @retry="groups.refetch()"
      @create="open()"
      @first-page="state.paginate(1, state.limit.value)"
      :busy="busy"
      @stock="openStock"
      @edit="open"
      @remove="
        deleting = $event;
        writeError = '';
      "
      @catalog="goCatalog"
      @publication="goPublication"
    />
    <OffsetPagination
      class="shrink-0"
      locale="ru"
      :total="groups.data.value?.total ?? 0"
      :page="Math.floor(state.offset.value / state.limit.value) + 1"
      :limit="state.limit.value"
      :limit-options="[25, 50, 100]"
      :disabled="!groups.data.value || groups.isFetching.value"
      @change="state.paginate($event.page, $event.limit)"
    />
    <Sheet :open="!!stockGroup" @update:open="!$event && (stockGroup = null)">
      <SheetContent class="w-full sm:max-w-3xl">
        <SheetHeader
          ><SheetTitle>Синхронизация остатков</SheetTitle
          ><SheetDescription
            >{{ stockGroup?.channelName }} ·
            {{
              stockGroup?.preview.catalogRoot?.title ?? "Связанные позиции"
            }}</SheetDescription
          ></SheetHeader
        >
        <BindingStockPanel
          v-if="stockGroup"
          :group="stockGroup"
          :state="stock.data.value"
          :loading="stock.isPending.value"
          :busy="stockBusy"
          :selected="stockSelected"
          :error="
            stockActionError ||
            (stock.error.value ? stockErrorMessage(stock.error.value) : '')
          "
          @select="stockSelected = $event"
          @refresh="stockAction('read')"
          @export="stockAction('write')"
          @repeat="repeatStock"
          @retry="stock.refetch()"
        />
      </SheetContent>
    </Sheet>
    <Sheet :open="!!state.groupId.value" @update:open="!$event && close()"
      ><SheetContent
        class="w-full gap-0 overflow-hidden sm:max-w-4xl"
        :show-close-button="false"
        @escape-key-down.prevent="close()"
        @interact-outside.prevent="close()"
      >
        <SheetHeader class="border-b p-5"
          ><div class="flex items-center justify-between gap-3">
            <SheetTitle>{{
              editId ? "Сопоставления группы" : "Новая связь"
            }}</SheetTitle
            ><Button variant="ghost" :disabled="busy" @click="close()"
              >Закрыть</Button
            >
          </div>
          <SheetDescription
            >Частичное сопоставление разрешено. Для смены карточки, канала или
            режима сначала снимите существующую связь.</SheetDescription
          ></SheetHeader
        >
        <div class="min-h-0 flex-1 space-y-6 overflow-y-auto p-5">
          <template v-if="!channelId"
            ><h3 class="font-medium">Выберите канал</h3>
            <input
              v-model="channelSearch"
              class="border-input h-10 w-full rounded-md border px-3"
              aria-label="Поиск канала"
              placeholder="Название канала"
              @input="channelOffset = 0" />
            <p v-if="channels.isPending.value">Загрузка каналов…</p>
            <Alert v-if="channels.error.value" variant="destructive"
              ><AlertDescription
                >{{ bindingError(channels.error.value) }}
                <Button @click="channels.refetch()"
                  >Повторить</Button
                ></AlertDescription
              ></Alert
            >
            <ul class="divide-y">
              <li
                v-for="c in channels.data.value?.items ?? []"
                :key="c.id"
                class="flex items-center justify-between py-3"
              >
                <span>{{ c.name }} · {{ c.platformKind }}</span
                ><Button variant="outline" @click="chooseChannel(c.id)"
                  >Выбрать канал</Button
                >
              </li>
            </ul>
            <OffsetPagination
              locale="ru"
              :total="channels.data.value?.total ?? 0"
              :limit="channels.data.value?.limit ?? 50"
              :page="
                Math.floor(channelOffset / (channels.data.value?.limit ?? 50)) +
                1
              "
              :limit-options="[50]"
              @change="channelOffset = ($event.page - 1) * $event.limit"
          /></template>
          <template v-else>
            <p class="font-medium">
              {{ channel.data.value?.name ?? "Канал" }} ·
              {{ channel.data.value?.platformKind }}
            </p>
            <p
              v-if="
                channel.data.value &&
                channel.data.value.verification.status !== 'verified'
              "
              class="text-muted-foreground text-sm"
            >
              Подключение сейчас не проверено. Локальное сопоставление доступно.
            </p>
            <p
              v-if="
                sync.data.value &&
                (sync.data.value.status !== 'completed' ||
                  sync.data.value.configRevision !==
                    channel.data.value?.configRevision)
              "
              class="text-sm text-muted-foreground"
            >
              Синхронизация ещё не завершена успешно для текущих настроек.
              Сопоставление опирается на уже полученные локальные позиции.
            </p>
            <Alert
              v-if="current.error.value || channel.error.value"
              variant="destructive"
              ><AlertDescription
                >{{ bindingError(current.error.value ?? channel.error.value) }}
                <Button
                  variant="outline"
                  @click="
                    current.refetch();
                    channel.refetch();
                  "
                  >Перечитать</Button
                ></AlertDescription
              ></Alert
            >
            <p v-if="editId && !loadedGroup" role="status">Загрузка группы…</p>
            <label class="grid gap-2 text-sm"
              >Режим<select
                :value="mode"
                :disabled="!!editId || busy"
                class="border-input bg-background h-10 rounded-md border px-2"
                @change="changeMode(($event.target as HTMLSelectElement).value)"
              >
                <option v-for="m in modes" :key="m" :value="m">
                  {{ bindingModes[m] }}
                </option>
              </select></label
            >
            <BindingCandidates
              v-if="!catalogId"
              title="Карточка Catalog"
              :busy="busy"
              :page="catalogCandidates.data.value"
              :pending="catalogCandidates.isFetching.value"
              :error="
                catalogCandidates.error.value
                  ? bindingError(catalogCandidates.error.value)
                  : ''
              "
              :search="catalogSearch"
              :offset="catalogOffset"
              :limit="catalogLimit"
              @search="catalogSearch = $event"
              @choose="catalogId = $event"
              @paginate="
                (p, l) => {
                  catalogOffset = (p - 1) * l;
                  catalogLimit = l;
                }
              "
              @retry="catalogCandidates.refetch()"
            />
            <template v-else>
              <section
                v-if="publicationId && !editId && mode === 'VARIABLE_TO_SIMPLE'"
                class="space-y-3 rounded-md border p-3"
              >
                <h3 class="font-medium">Новая независимая группа</h3>
                <p class="text-sm text-muted-foreground">
                  Сохранение создаст отдельную группу. Чтобы дополнить
                  существующее сопоставление этой карточки, выберите группу
                  ниже.
                </p>
                <p v-if="compatible.isPending.value" class="text-sm">
                  Проверяем существующие группы…
                </p>
                <p
                  v-if="compatible.error.value"
                  class="text-sm text-destructive"
                >
                  {{ bindingError(compatible.error.value) }}
                  <Button
                    variant="outline"
                    size="sm"
                    @click="compatible.refetch()"
                    >Повторить</Button
                  >
                </p>
                <ul class="divide-y">
                  <li
                    v-for="g in compatible.data.value?.items ?? []"
                    :key="g.id"
                    class="flex flex-wrap items-center justify-between gap-2 py-2"
                  >
                    <span class="text-sm"
                      >Группа {{ g.id.slice(0, 8) }} · {{ g.items.length }} пар
                      · {{ bindingStates[g.preview.state] }}</span
                    ><Button variant="outline" size="sm" @click="open(g)"
                      >Добавить в эту группу</Button
                    >
                  </li>
                </ul>
                <OffsetPagination
                  v-if="compatible.data.value?.total"
                  locale="ru"
                  :total="compatible.data.value.total"
                  :page="Math.floor(compatibleOffset / compatibleLimit) + 1"
                  :limit="compatibleLimit"
                  :limit-options="[25, 50, 100]"
                  @change="
                    compatibleOffset = ($event.page - 1) * $event.limit;
                    compatibleLimit = $event.limit;
                  "
                />
              </section>
              <p class="text-sm">
                Catalog:
                {{ preview.data.value?.catalogRoot?.title ?? catalogId }}
                <Button
                  v-if="!editId && !catalogRootId"
                  :disabled="busy"
                  size="sm"
                  variant="link"
                  @click="
                    catalogId = '';
                    items = [];
                  "
                  >Изменить выбор</Button
                >
              </p>
              <BindingCandidates
                v-if="!publicationRoot || mode === 'VARIABLE_TO_SIMPLE'"
                :busy="busy"
                :title="
                  mode === 'VARIABLE_TO_SIMPLE'
                    ? 'Самостоятельные публикации (выберите позиции для списка)'
                    : 'Карточка площадки'
                "
                :page="publicationCandidates.data.value"
                :pending="publicationCandidates.isFetching.value"
                :error="
                  publicationCandidates.error.value
                    ? bindingError(publicationCandidates.error.value)
                    : ''
                "
                :search="publicationSearch"
                :offset="publicationOffset"
                :limit="publicationLimit"
                :allowed-ids="allowed"
                @search="publicationSearch = $event"
                @choose="choosePublication"
                @paginate="
                  (p, l) => {
                    publicationOffset = (p - 1) * l;
                    publicationLimit = l;
                  }
                "
                @retry="publicationCandidates.refetch()"
              />
              <p
                v-if="publicationRoot && mode !== 'VARIABLE_TO_SIMPLE'"
                class="text-muted-foreground text-sm"
              >
                Внешняя карточка: {{ publicationRoot }}
                <Button
                  v-if="!editId && !publicationId"
                  :disabled="busy"
                  variant="link"
                  size="sm"
                  @click="
                    publicationRoot = null;
                    items = [];
                  "
                  >Изменить выбор</Button
                >
              </p>
              <p
                v-if="preview.isFetching.value"
                class="text-sm text-muted-foreground"
                role="status"
              >
                Проверка структуры…
              </p>
              <Alert v-if="preview.error.value" variant="destructive"
                ><AlertDescription
                  >{{ bindingError(preview.error.value) }}
                  <Button variant="outline" @click="preview.refetch()"
                    >Повторить проверку</Button
                  ></AlertDescription
                ></Alert
              >
              <p
                v-if="
                  publicationId &&
                  !editId &&
                  mode === 'VARIABLE_TO_SIMPLE' &&
                  !items.some((p) => p.publicationId === publicationId)
                "
                class="text-muted-foreground text-sm"
              >
                Сопоставьте текущую публикацию с одной из позиций Catalog.
              </p>
              <BindingPairsForm
                :context-publication-id="publicationId"
                :primary-publication-id="
                  mode === 'VARIABLE_TO_VARIABLE' &&
                  channel.data.value?.platformKind === 'prom'
                    ? (publicationRoot ?? undefined)
                    : undefined
                "
                v-if="preview.data.value"
                :catalog="preview.data.value.catalogPositions"
                :publications="
                  mode === 'VARIABLE_TO_SIMPLE'
                    ? options
                    : preview.data.value.publications
                "
                :items="items"
                :occupied="occupied"
                :busy="busy || (!!editId && !loadedGroup)"
                @pair="pair"
                @suggest="suggest"
              />
              <p v-if="preview.data.value" class="text-sm">
                {{ bindingStates[preview.data.value.state] }} · Сопоставлено
                {{ items.length }} · Catalog:
                {{ preview.data.value.catalogCount }} · Площадка:
                {{ preview.data.value.publicationCount }}
              </p>
              <ul
                v-if="preview.data.value?.issues.length"
                class="text-sm text-destructive space-y-1"
                role="alert"
              >
                <li v-for="issue in preview.data.value.issues" :key="issue">
                  {{ bindingIssueLabels[issue] ?? issue }}
                </li>
              </ul>
              <p
                v-if="
                  loadedGroup?.items.some(
                    (p) =>
                      !preview.data.value?.catalogPositions.some(
                        (c) => c.id === p.catalogId,
                      ),
                  )
                "
                class="text-sm text-destructive"
              >
                В группе есть отсутствующие позиции Catalog. Снимите группу и
                создайте корректную связь.
              </p>
            </template>
          </template>
          <Alert v-if="writeError" variant="destructive"
            ><AlertDescription
              >{{ writeError }}
              <Button
                v-if="editId"
                variant="outline"
                size="sm"
                @click="reloadGroup"
                >Перечитать группу</Button
              ></AlertDescription
            ></Alert
          >
          <Alert v-if="uncertain"
            ><AlertDescription
              >Результат создания не подтверждён. Список связей обновлён;
              закройте редактор и проверьте его перед новым
              созданием.</AlertDescription
            ></Alert
          >
        </div>
        <footer class="flex flex-wrap justify-end gap-3 border-t p-4">
          <Button
            variant="outline"
            :disabled="busy || !ready"
            @click="preview.refetch()"
            >Повторить проверку</Button
          ><Button
            :disabled="
              busy ||
              !ready ||
              uncertain ||
              (!editId && sourceAlreadyBound) ||
              (!!publicationId &&
                !editId &&
                mode === 'VARIABLE_TO_SIMPLE' &&
                !items.some((p) => p.publicationId === publicationId)) ||
              !items.length ||
              !preview.data.value ||
              preview.isFetching.value ||
              preview.isError.value ||
              !!preview.data.value?.issues.length
            "
            @click="save"
            >{{ busy ? "Сохраняем…" : "Сохранить связь" }}</Button
          >
        </footer>
      </SheetContent></Sheet
    >
    <AlertDialog :open="confirmDiscard" @update:open="!$event && discard(false)"
      ><AlertDialogContent
        ><AlertDialogHeader
          ><AlertDialogTitle>Отказаться от изменений?</AlertDialogTitle
          ><AlertDialogDescription
            >Несохранённые соответствия будут потеряны. Существующая группа
            останется без изменений.</AlertDialogDescription
          ></AlertDialogHeader
        ><AlertDialogFooter
          ><AlertDialogCancel @click="discard(false)"
            >Продолжить редактирование</AlertDialogCancel
          ><Button @click="discard(true)"
            >Отказаться от изменений</Button
          ></AlertDialogFooter
        ></AlertDialogContent
      ></AlertDialog
    >
    <AlertDialog
      :open="!!deleting"
      @update:open="!busy && !$event && (deleting = null)"
      ><AlertDialogContent
        ><AlertDialogHeader
          ><AlertDialogTitle>Снять группу связей?</AlertDialogTitle
          ><AlertDialogDescription
            >Все пары этой группы будут удалены. Публикации и товары Catalog
            сохранятся. Чтобы перенести публикацию на другую карточку, после
            снятия создайте новую связь.</AlertDialogDescription
          ></AlertDialogHeader
        >
        <p v-if="writeError" class="text-sm text-destructive" role="alert">
          {{ writeError }}
        </p>
        <AlertDialogFooter
          ><AlertDialogCancel :disabled="busy">Отмена</AlertDialogCancel
          ><Button :disabled="busy" @click="unlink">{{
            busy ? "Снимаем…" : "Снять связь"
          }}</Button></AlertDialogFooter
        ></AlertDialogContent
      ></AlertDialog
    >
  </section>
</template>
