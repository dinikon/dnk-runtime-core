<script setup lang="ts">
import { useSalesColumnOffsets } from "../model/use-sales-column-offsets";
import { useSalesContactPreview } from "../model/sales.queries";
import { useSalesScroll } from "../model/use-sales-scroll";
import {
  useSalesMutations,
  useSalesContactSeed,
} from "../model/sales.mutations";
import { computed, ref, watch, onScopeDispose } from "vue";
import { useRouter, onBeforeRouteLeave } from "vue-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useFunnelOptions as useFunnels, useFunnel } from "@/modules/funnel";
import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import { useSalesPageState } from "../model/use-sales-page-state";
import {
  useSalesPeople,
  useSalesList,
  useSalesColumns,
  useContactPointLabels,
  useSalesScope,
} from "../model/sales.queries";
import { cloneSaleValue, emptySaleDraft } from "../model/sales.draft";
import type { SalesKind, SaleSummary } from "../model/sales.types";
import SalesFeedback from "../ui/sales/SalesFeedback.vue";
import SalesResults from "../ui/sales/SalesResults.vue";
import type { SalesColumn } from "../ui/sales/SalesResults.vue";
import CreateSaleDialog from "../ui/sales/CreateSaleDialog.vue";
import MoveSaleDialog from "../ui/sales/MoveSaleDialog.vue";
import UnsavedChangesDialog from "../ui/sales/UnsavedChangesDialog.vue";
const props = defineProps<{ kind: SalesKind }>(),
  router = useRouter(),
  kind = computed(() => props.kind),
  modelKey = computed(() => (props.kind === "leads" ? "crm.lead" : "crm.deal")),
  scope = useSalesScope();
const state = useSalesPageState(() => props.kind),
  funnelPage = useFunnels(modelKey),
  funnel = useFunnel(computed(() => state.filters.value.funnelId));
watch(
  () => funnelPage.data.value,
  (v) => {
    if (!state.filters.value.funnelId && v) {
      const item = v.items.find((f) => f.isDefault);
      if (item) void state.set({ funnel: item.id });
    }
  },
  { immediate: true },
);
const scrollElement = ref<HTMLElement | null>(null);
useSalesScroll(
  scrollElement,
  () => scope.value.join("|") + "|" + router.currentRoute.value.fullPath,
);
const ready = computed(
    () => !!funnel.data.value && funnel.data.value.modelKey === modelKey.value,
  ),
  view = state.view;
const list = useSalesList(
  kind,
  state.filters,
  computed(() => ready.value && view.value === "list"),
);
const offsets = useSalesColumnOffsets(
  () => scope.value.join("|") + "|" + router.currentRoute.value.fullPath,
);
const columns = useSalesColumns(
  kind,
  computed(() => funnel.data.value),
  state.filters,
  offsets,
  computed(() => ready.value && view.value === "kanban"),
);
function resetColumns() {
  offsets.value = {};
}
watch(
  () => [
    props.kind,
    state.filters.value.funnelId,
    state.filters.value.stageId,
    state.filters.value.search,
    state.filters.value.converted,
    state.filters.value.sort,
  ],
  resetColumns,
);
const columnModels = computed<SalesColumn[]>(() =>
  columns.columns.value.map((c) => ({
    ...c,
    error: c.error
      ? getApiErrorMessage(c.error, "Не удалось загрузить стадию.")
      : "",
  })),
);
const people = useSalesPeople(),
  labels = useContactPointLabels(),
  mutations = useSalesMutations(),
  seed = useSalesContactSeed();
const contacts = computed(() =>
    (people.contacts.data.value ?? []).map((c) => ({
      id: c.id,
      label: c.displayName,
    })),
  ),
  companies = computed(() =>
    (people.companies.data.value ?? []).map((c) => ({
      id: c.id,
      label: c.legalName,
    })),
  );
const contactNames = computed(() =>
    Object.fromEntries(contacts.value.map((c) => [c.id, c.label])),
  ),
  companyNames = computed(() =>
    Object.fromEntries(companies.value.map((c) => [c.id, c.label])),
  );
const createOpen = ref(false),
  draft = ref(emptySaleDraft()),
  error = ref(""),
  createError = ref(""),
  moving = ref<SaleSummary | null>(null),
  movingId = ref(""),
  failedMove = ref<SaleSummary | null>(null),
  guardOpen = ref(false),
  guardMessage = ref("");
let guarded: (() => void) | null = null;
let navigationResolve: ((v: boolean) => void) | null = null;
const createDirty = computed(
  () =>
    createOpen.value &&
    JSON.stringify(draft.value) !==
      JSON.stringify(emptySaleDraft(state.filters.value.funnelId)),
);
function ask(action: () => void, message = "") {
  guarded = action;
  guardMessage.value = message;
  guardOpen.value = true;
}
function stay() {
  guardOpen.value = false;
  guarded = null;
  navigationResolve?.(false);
  navigationResolve = null;
}
function discard() {
  guardOpen.value = false;
  const action = guarded;
  guarded = null;
  action?.();
  navigationResolve?.(true);
  navigationResolve = null;
}
function closeCreate() {
  if (mutations.create.isPending.value) return;
  if (createDirty.value) ask(() => (createOpen.value = false));
  else createOpen.value = false;
}
function startCreate() {
  createError.value = "";
  draft.value = emptySaleDraft(state.filters.value.funnelId);
  createOpen.value = true;
}
function open(record: SaleSummary) {
  void router.push({
    path: "/crm/" + props.kind + "/" + record.id,
    query: { returnTo: router.currentRoute.value.fullPath },
  });
}
async function create() {
  if (mutations.create.isPending.value) return;
  const context = scope.value.join("|");
  createError.value = "";
  try {
    const result = await mutations.create.mutateAsync({
      kind: props.kind,
      draft: cloneSaleValue(draft.value),
    });
    if (context !== scope.value.join("|")) return;
    createOpen.value = false;
    await router.push({
      path: "/crm/" + props.kind + "/" + result.id,
      query: { returnTo: router.currentRoute.value.fullPath },
    });
  } catch (e) {
    if (context !== scope.value.join("|")) return;
    createError.value = getApiErrorStatus(e)
      ? getApiErrorMessage(e, "Не удалось выполнить действие.")
      : "Результат создания неизвестен. Проверьте список перед повторной отправкой.";
  }
}
async function copyContact(id: string) {
  const action = async () => {
    const context = scope.value.join("|");
    try {
      const result = await seed.mutateAsync(id);
      if (context !== scope.value.join("|")) return;
      draft.value = {
        ...draft.value,
        contactId: id,
        firstName: result.contact.firstName,
        lastName: result.contact.lastName ?? "",
        middleName: result.contact.middleName ?? "",
        points: {
          phones: result.points.phones.map((p) => ({
            ...p,
            clientKey: crypto.randomUUID(),
            bindingId: undefined,
            contactPointId: undefined,
          })),
          emails: result.points.emails.map((p) => ({
            ...p,
            clientKey: crypto.randomUUID(),
            bindingId: undefined,
            contactPointId: undefined,
          })),
        },
      };
    } catch (e) {
      if (context !== scope.value.join("|")) return;
      createError.value = getApiErrorMessage(
        e,
        "Не удалось выполнить действие.",
      );
    }
  };
  if (
    draft.value.firstName ||
    draft.value.lastName ||
    draft.value.points.phones.length ||
    draft.value.points.emails.length
  )
    ask(
      () => void action(),
      "Заменить введённые ФИО, телефоны и email данными выбранного контакта?",
    );
  else await action();
}
async function verifyMove(record: SaleSummary): Promise<boolean> {
  const context = scope.value.join("|");
  try {
    await mutations.verify(record.kind, record.id);
    if (context !== scope.value.join("|")) return false;
    await mutations.refresh();
    moving.value = null;
    failedMove.value = null;
    return true;
  } catch {
    if (context === scope.value.join("|")) {
      failedMove.value = record;
      error.value =
        "Не удалось проверить положение карточки. Проверьте его перед следующим переносом.";
    }
    return false;
  }
}
async function retryMove() {
  const record = failedMove.value;
  if (record && (await verifyMove(record))) {
    movingId.value = "";
    resetColumns();
  }
}
async function move(record: SaleSummary, stageId: string) {
  if (movingId.value) return;
  const context = scope.value.join("|");
  error.value = "";
  movingId.value = record.id;
  let verified = true;
  try {
    await mutations.position.mutateAsync({ record, stageId });
    if (context !== scope.value.join("|")) return;
    moving.value = null;
    resetColumns();
  } catch (e) {
    if (context !== scope.value.join("|")) return;
    error.value =
      getApiErrorStatus(e) === 409
        ? "Карточка уже изменена. Проверяем её актуальное положение."
        : getApiErrorStatus(e) && getApiErrorStatus(e)! < 500
          ? getApiErrorMessage(e, "Не удалось переместить карточку.")
          : "Результат перемещения неизвестен. Сначала проверяем карточку.";
    verified = await verifyMove(record);
    resetColumns();
  } finally {
    if (verified && context === scope.value.join("|")) movingId.value = "";
  }
}
function more(stageId: string) {
  offsets.value = {
    ...offsets.value,
    [stageId]: (offsets.value[stageId] ?? 0) + 20,
  };
}
function retry(stageId?: string) {
  if (stageId) {
    void columns.retry(stageId);
  } else void list.refetch();
}
onBeforeRouteLeave(() => {
  if (mutations.create.isPending.value || seed.isPending.value) return false;
  if (!createDirty.value) return true;
  return new Promise<boolean>((resolve) => {
    navigationResolve = resolve;
    ask(() => (createOpen.value = false));
  });
});
watch(
  () => scope.value.join("|"),
  () => {
    stay();
    mutations.create.reset();
    mutations.position.reset();
    seed.reset();
    createOpen.value = false;
    draft.value = emptySaleDraft();
    moving.value = null;
    movingId.value = "";
    failedMove.value = null;
    error.value = "";
    createError.value = "";
    resetColumns();
  },
);
onScopeDispose(() => navigationResolve?.(false));
const contactPreview = useSalesContactPreview(
  computed(() => draft.value.contactId),
  computed(() => createOpen.value && kind.value === "leads"),
);
</script>
<template>
  <div
    ref="scrollElement"
    class="flex min-h-0 min-w-0 flex-col gap-5 overflow-y-auto pb-6"
  >
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p class="text-sm text-muted-foreground">CRM</p>
        <h1 class="text-2xl font-semibold">
          {{ kind === "leads" ? "Лиды" : "Сделки" }}
        </h1>
        <p class="mt-1 text-sm text-muted-foreground">
          {{
            kind === "leads"
              ? "Обращения клиентов и подготовка продаж."
              : "Единая карточка продажи товаров и услуг."
          }}
        </p>
      </div>
      <Button
        :disabled="!ready || !scope[0] || !scope[1]"
        @click="startCreate"
        >{{ kind === "leads" ? "Новый лид" : "Новая сделка" }}</Button
      >
    </header>
    <div class="flex flex-wrap items-center gap-3">
      <NativeSelect
        aria-label="Текущая воронка"
        :model-value="state.filters.value.funnelId"
        @update:model-value="
          state.set({
            funnel: String($event),
            stage: undefined,
            page: undefined,
          })
        "
        ><option v-if="!state.filters.value.funnelId" value="">
          Выберите воронку
        </option>
        <option
          v-for="f in funnelPage.data.value?.items ?? []"
          :key="f.id"
          :value="f.id"
        >
          {{ f.name }}
        </option></NativeSelect
      ><ToggleGroup
        type="single"
        :model-value="view"
        aria-label="Вид коллекции"
        @update:model-value="
          state.set({ view: String($event) || 'kanban', page: undefined })
        "
        ><ToggleGroupItem value="kanban">Канбан</ToggleGroupItem
        ><ToggleGroupItem value="list">Список</ToggleGroupItem></ToggleGroup
      ><Button
        variant="outline"
        :disabled="!ready"
        @click="router.push('/funnels/' + state.filters.value.funnelId)"
        >Настроить воронку</Button
      ><Button variant="ghost" @click="router.push('/funnels')"
        >Все воронки</Button
      >
    </div>
    <div class="flex flex-wrap gap-3">
      <Input
        v-model="state.input.value"
        class="max-w-sm"
        aria-label="Поиск карточек"
        placeholder="Поиск по названию или клиенту"
      /><NativeSelect
        aria-label="Фильтр стадии"
        :model-value="state.filters.value.stageId"
        @update:model-value="
          state.set({ stage: String($event) || undefined, page: undefined })
        "
        ><option value="">Все стадии</option>
        <option
          v-for="s in funnel.data.value?.stages ?? []"
          :key="s.id"
          :value="s.id"
        >
          {{ s.name }}
        </option></NativeSelect
      ><NativeSelect
        v-if="kind === 'leads'"
        aria-label="Состояние конвертации"
        :model-value="
          state.filters.value.converted === undefined
            ? 'all'
            : state.filters.value.converted
              ? 'yes'
              : 'no'
        "
        @update:model-value="
          state.set({ converted: String($event), page: undefined })
        "
        ><option value="no">Неконвертированные</option>
        <option value="yes">Конвертированные</option>
        <option value="all">Все лиды</option></NativeSelect
      ><NativeSelect
        aria-label="Сортировка"
        :model-value="state.filters.value.sort"
        @update:model-value="
          state.set({ sort: String($event), page: undefined })
        "
        ><option value="updated">По времени изменения</option>
        <option value="title">По названию</option></NativeSelect
      ><Button
        variant="ghost"
        @click="
          state.set({
            q: undefined,
            stage: undefined,
            converted: undefined,
            page: undefined,
            sort: undefined,
          })
        "
        >Сбросить фильтры</Button
      >
    </div>
    <Alert v-if="error" variant="destructive"
      ><AlertDescription role="alert"
        >{{ error
        }}<Button v-if="failedMove" variant="outline" @click="retryMove"
          >Проверить положение</Button
        ></AlertDescription
      ></Alert
    ><SalesFeedback
      :loading="
        funnelPage.isPending.value ||
        (!!state.filters.value.funnelId && funnel.isPending.value)
      "
      :error="
        funnelPage.isError.value
          ? 'Не удалось загрузить воронки'
          : funnel.isError.value
            ? 'Указанная воронка недоступна. Выберите другую.'
            : funnel.data.value && funnel.data.value.modelKey !== modelKey
              ? 'Воронка другого типа. Выберите подходящую.'
              : ''
      "
      @retry="
        funnelPage.refetch();
        funnel.refetch();
      "
      ><SalesResults
        :view="view"
        :columns="columnModels"
        :items="list.data.value?.items ?? []"
        :stages="funnel.data.value?.stages ?? []"
        :contact-names="contactNames"
        :company-names="companyNames"
        :moving-id="movingId"
        :busy="!!movingId"
        :filtered="
          !!state.filters.value.search ||
          !!state.filters.value.stageId ||
          state.filters.value.converted === true
        "
        :fetching="list.isFetching.value"
        :total="list.data.value?.total ?? 0"
        :offset="state.filters.value.offset"
        :loading="list.isPending.value"
        :error="
          list.error.value
            ? getApiErrorMessage(
                list.error.value,
                'Не удалось выполнить действие.',
              )
            : ''
        "
        @open="open"
        @move="moving = $event"
        @drop="move"
        @more="more"
        @retry="retry"
        @page="state.set({ page: String($event) })" /></SalesFeedback
    ><CreateSaleDialog
      :open="createOpen"
      :model-value="draft"
      @update:model-value="draft = $event"
      :kind="kind"
      :people-loading="
        people.contacts.isPending.value || people.companies.isPending.value
      "
      :people-error="
        people.contacts.isError.value || people.companies.isError.value
      "
      @retry-people="
        people.contacts.refetch();
        people.companies.refetch();
      "
      :funnels="funnelPage.data.value?.items ?? []"
      :contacts="contacts"
      :contact-preview="contactPreview.data.value"
      :preview-loading="contactPreview.isPending.value"
      :preview-error="contactPreview.isError.value"
      :companies="companies"
      :labels="labels.data.value ?? []"
      :labels-loading="labels.isPending.value"
      :labels-error="labels.isError.value"
      :pending="mutations.create.isPending.value || seed.isPending.value"
      :error="createError"
      @submit="create"
      @close="closeCreate"
      @copy-contact="copyContact"
    /><MoveSaleDialog
      :open="!!moving"
      :title="moving?.title ?? ''"
      :current-id="moving?.stageId ?? ''"
      :stages="funnel.data.value?.stages ?? []"
      :funnels="[]"
      :pending="mutations.position.isPending.value"
      @update:open="!$event && (moving = null)"
      @submit="moving && move(moving, $event)"
    /><UnsavedChangesDialog
      :open="guardOpen"
      :message="guardMessage || undefined"
      @stay="stay"
      @discard="discard"
    />
  </div>
</template>
