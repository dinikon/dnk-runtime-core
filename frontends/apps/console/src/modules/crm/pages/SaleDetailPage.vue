<script setup lang="ts">
import { useCatalogSearch } from "../model/use-catalog-search";
import { useSalesContactPreview } from "../model/sales.queries";
import { nextTick } from "vue";
import { validateContactPoints } from "@/modules/contact-points";
import {
  useSalesMutations,
  useSalesContactSeed,
  useSalesCatalogSelection,
} from "../model/sales.mutations";
import { computed, ref, watch, onMounted, onScopeDispose } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useFunnel, useFunnelOptions as useFunnels } from "@/modules/funnel";
import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import {
  useSale,
  useSalesScope,
  useSalesPeople,
  useContactPointLabels,
  useConversionContext,
  useSalesCatalog,
} from "../model/sales.queries";
import {
  cloneSaleValue,
  emptySaleDraft,
  saleDraft,
  newBasketLine,
  validateSaleDraft,
} from "../model/sales.draft";
import type {
  SalesKind,
  SaleDraft,
  ConversionSubmission,
  ConversionResult,
} from "../model/sales.types";
import SalesFeedback from "../ui/sales/SalesFeedback.vue";
import SaleFields from "../ui/sales/SaleFields.vue";
import SalePointsEditor from "../ui/sales/SalePointsEditor.vue";
import BasketEditor from "../ui/basket/BasketEditor.vue";
import CatalogPicker from "../ui/sales/CatalogPicker.vue";
import MoveSaleDialog from "../ui/sales/MoveSaleDialog.vue";
import UnsavedChangesDialog from "../ui/sales/UnsavedChangesDialog.vue";
import ConversionDialog from "../ui/sales/ConversionDialog.vue";
const titleElement = ref<HTMLElement | null>(null);
const props = defineProps<{ kind: SalesKind }>(),
  route = useRoute(),
  router = useRouter(),
  kind = computed(() => props.kind),
  id = computed(() => String(route.params.id)),
  scope = useSalesScope(),
  detail = useSale(kind, id),
  record = computed(() => detail.data.value),
  modelKey = computed(() => (kind.value === "leads" ? "crm.lead" : "crm.deal"));
const funnels = useFunnels(modelKey),
  dealFunnels = useFunnels(computed(() => "crm.deal")),
  funnel = useFunnel(computed(() => record.value?.funnelId ?? ""));
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
const draft = ref(emptySaleDraft()),
  baseline = ref(emptySaleDraft()),
  editing = ref(false),
  error = ref(""),
  notice = ref("");
const dirty = computed(
    () => JSON.stringify(draft.value) !== JSON.stringify(baseline.value),
  ),
  frozen = computed(() => !!record.value?.conversionResult),
  pending = computed(
    () =>
      mutations.update.isPending.value ||
      mutations.position.isPending.value ||
      mutations.convert.isPending.value,
  );
function apply() {
  if (!record.value) return;
  baseline.value = saleDraft(record.value);
  draft.value = cloneSaleValue(baseline.value);
}
watch(
  record,
  (v) => {
    if (v && !editing.value && !mutations.update.isPending.value) apply();
  },
  { immediate: true },
);
const positionUnverified = ref(false);
const catalogState = useCatalogSearch();
const moveOpen = ref(false),
  transferOpen = ref(false),
  catalogOpen = ref(false),
  catalogInput = catalogState.input,
  catalogSearch = catalogState.search,
  catalog = useSalesCatalog(catalogSearch, catalogOpen),
  catalogSelect = useSalesCatalogSelection();
const guardOpen = ref(false),
  guardMessage = ref("");
let guarded: (() => void) | null = null;
let navigationResolve: ((v: boolean) => void) | null = null;
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
  if (!guardMessage.value) {
    apply();
    editing.value = false;
  }
  action?.();
  navigationResolve?.(true);
  navigationResolve = null;
}
function afterClean(action: () => void) {
  if (dirty.value) ask(action);
  else {
    editing.value = false;
    action();
  }
}
async function save(): Promise<boolean> {
  if (!record.value || pending.value) return false;
  const invalid =
    validateSaleDraft(draft.value) ??
    (kind.value === "leads" &&
    ["phone", "email"].some(
      (k) =>
        Object.keys(
          validateContactPoints(
            k === "phone"
              ? draft.value.points.phones
              : draft.value.points.emails,
            k as "phone" | "email",
          ),
        ).length,
    )
      ? "Проверьте телефоны и email."
      : null);
  if (invalid) {
    error.value = invalid;
    return false;
  }
  const sent = cloneSaleValue(draft.value),
    previous = cloneSaleValue(baseline.value),
    context = scope.value.join("|"),
    savedId = id.value;
  error.value = "";
  try {
    const result = await mutations.update.mutateAsync({
      kind: kind.value,
      id: savedId,
      draft: sent,
      previous,
    });
    if (context !== scope.value.join("|") || savedId !== id.value) return false;
    const fresh = await detail.refetch();
    if (context !== scope.value.join("|") || savedId !== id.value) return false;
    if (!fresh.data)
      throw new Error(
        "Изменения отправлены, но карточку не удалось перечитать.",
      );
    const saved = saleDraft(fresh.data),
      current = cloneSaleValue(draft.value);
    for (const key of Object.keys(saved) as (keyof SaleDraft)[])
      if (JSON.stringify(current[key]) === JSON.stringify(sent[key]))
        Object.assign(current, { [key]: saved[key] });
    current.basketRevision = saved.basketRevision;
    current.items = current.items.map((item) => {
      if (item.id) return item;
      const savedLineId = result.lineIdMap[item.clientLineKey];
      return savedLineId ? { ...item, id: savedLineId } : item;
    });
    for (const group of ["phones", "emails"] as const)
      current.points[group] = current.points[group].map((p) => {
        const found = saved.points[group].find((v) => v.value === p.value);
        return found
          ? {
              ...p,
              bindingId: found.bindingId,
              contactPointId: found.contactPointId,
            }
          : p;
      });
    baseline.value = saved;
    draft.value = current;
    notice.value = "Изменения сохранены.";
    if (!dirty.value) editing.value = false;
    return true;
  } catch (e) {
    if (context !== scope.value.join("|") || savedId !== id.value) return false;
    error.value =
      getApiErrorStatus(e) === 409
        ? "Корзина или карточка изменена другим пользователем. Ваш ввод сохранён. Сверьте его с актуальными данными."
        : getApiErrorStatus(e)
          ? getApiErrorMessage(e, "Не удалось выполнить действие.")
          : "Не удалось подтвердить сохранение. Ваш ввод сохранён; проверьте актуальную карточку перед повтором.";
    return false;
  }
}
async function saveGuard() {
  if (await save()) {
    if (dirty.value) {
      error.value =
        "После отправки появились новые изменения. Сохраните их перед переходом.";
      return;
    }
    discard();
  }
}
async function verifyPosition(): Promise<void> {
  const context = scope.value.join("|"),
    savedId = id.value;
  const response = await detail.refetch();
  if (context !== scope.value.join("|") || savedId !== id.value) return;
  positionUnverified.value = response.isError;
  if (response.isError)
    error.value =
      "Не удалось проверить положение. Повторите проверку перед следующим переносом.";
}
async function position(target: string, transfer = false) {
  if (!record.value || positionUnverified.value || pending.value) return;
  const context = scope.value.join("|"),
    savedId = id.value;
  error.value = "";
  try {
    await mutations.position.mutateAsync({
      record: record.value,
      ...(transfer ? { funnelId: target } : { stageId: target }),
    });
    if (context !== scope.value.join("|") || savedId !== id.value) return;
    moveOpen.value = false;
    transferOpen.value = false;
    await verifyPosition();
  } catch (e) {
    if (context !== scope.value.join("|") || savedId !== id.value) return;
    error.value =
      getApiErrorStatus(e) === 409
        ? "Положение карточки уже изменено. Загружаем актуальную стадию."
        : getApiErrorStatus(e) && getApiErrorStatus(e)! < 500
          ? getApiErrorMessage(e, "Не удалось переместить карточку.")
          : "Результат перемещения неизвестен. Проверяем актуальное положение; повтор автоматически не отправляется.";
    await verifyPosition();
    moveOpen.value = false;
    transferOpen.value = false;
  }
}
async function addCatalog(itemId: string) {
  const context = scope.value.join("|"),
    savedId = id.value;
  try {
    const item = await catalogSelect.mutateAsync(itemId);
    if (context !== scope.value.join("|") || savedId !== id.value) return;
    draft.value.items.push({
      ...newBasketLine(),
      catalogItemId: item.id,
      name: item.title,
      kind: item.kind,
      sku: item.sku,
      unitPrice:
        item.currency === draft.value.currency && item.price !== null
          ? item.price
          : "",
    });
    catalogOpen.value = false;
    if (item.currency !== draft.value.currency || item.price === null)
      notice.value =
        "Укажите цену позиции в валюте продажи. Валюта цены каталога не определена или отличается.";
  } catch (e) {
    if (context !== scope.value.join("|") || savedId !== id.value) return;
    error.value = getApiErrorMessage(e, "Не удалось выполнить действие.");
  }
}
async function copyContact(contactId: string) {
  const action = async () => {
    const context = scope.value.join("|"),
      savedId = id.value;
    try {
      const value = await seed.mutateAsync(contactId);
      if (context !== scope.value.join("|") || savedId !== id.value) return;
      draft.value = {
        ...draft.value,
        contactId,
        firstName: value.contact.firstName,
        lastName: value.contact.lastName ?? "",
        middleName: value.contact.middleName ?? "",
        points: {
          phones: value.points.phones.map((p) => ({
            ...p,
            clientKey: crypto.randomUUID(),
            bindingId: undefined,
            contactPointId: undefined,
          })),
          emails: value.points.emails.map((p) => ({
            ...p,
            clientKey: crypto.randomUUID(),
            bindingId: undefined,
            contactPointId: undefined,
          })),
        },
      };
    } catch (e) {
      if (context !== scope.value.join("|") || savedId !== id.value) return;
      error.value = getApiErrorMessage(e, "Не удалось выполнить действие.");
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
const conversionOpen = ref(false),
  conversionResult = ref<ConversionResult | null>(null),
  conversion = useConversionContext(
    id,
    computed(() => conversionOpen.value && !conversionResult.value),
  ),
  conversionError = ref(""),
  uncertain = ref(false);
let conversionRequest: {
  submission: ConversionSubmission;
  key: string;
} | null = null;
function openConversion() {
  afterClean(() => {
    conversionError.value = "";
    conversionResult.value = null;
    uncertain.value = false;
    conversionRequest = null;
    conversionOpen.value = true;
    void conversion.refetch();
  });
}
async function convert(submission?: ConversionSubmission) {
  if (mutations.convert.isPending.value) return;
  if (submission)
    conversionRequest = {
      submission: cloneSaleValue(submission),
      key: crypto.randomUUID(),
    };
  if (!conversionRequest) return;
  const context = scope.value.join("|");
  conversionError.value = "";
  try {
    const result = await mutations.convert.mutateAsync({
      id: id.value,
      ...conversionRequest,
    });
    if (context !== scope.value.join("|")) return;
    conversionResult.value = result;
    uncertain.value = false;
    editing.value = false;
    await detail.refetch();
  } catch (e) {
    if (context !== scope.value.join("|")) return;
    uncertain.value = !getApiErrorStatus(e) || getApiErrorStatus(e)! >= 500;
    conversionError.value = uncertain.value
      ? "Ответ не получен. Сначала проверьте результат или безопасно повторите тот же запрос."
      : getApiErrorMessage(e, "Не удалось выполнить действие.");
  }
}
async function checkConversion() {
  const context = scope.value.join("|"),
    savedId = id.value;
  const response = await detail.refetch();
  if (context !== scope.value.join("|") || savedId !== id.value) return;
  if (response.data?.conversionResult) {
    conversionResult.value = response.data.conversionResult;
    uncertain.value = false;
    editing.value = false;
  } else
    conversionError.value = response.isError
      ? "Не удалось проверить результат. Безопасный повтор использует прежний ключ."
      : "Конвертация пока не подтверждена. Можно безопасно повторить прежний запрос.";
}
async function refreshConversion() {
  uncertain.value = false;
  conversionRequest = null;
  conversionError.value = "";
  await conversion.refetch();
}
watch(
  () => conversion.error.value,
  (error) => {
    if (conversionOpen.value && getApiErrorStatus(error) === 409)
      void checkConversion();
  },
);
function back() {
  const target = route.query.returnTo;
  void router.push(
    typeof target === "string" &&
      target.startsWith("/crm/" + kind.value) &&
      !target.startsWith("//")
      ? target
      : "/crm/" + kind.value,
  );
}
function leave() {
  if (pending.value) return false;
  if (!dirty.value) return true;
  return new Promise<boolean>((resolve) => {
    navigationResolve = resolve;
    ask(() => {});
  });
}
onBeforeRouteLeave(leave);
onBeforeRouteUpdate(leave);
const unload = (event: BeforeUnloadEvent) => {
  if (dirty.value || pending.value) {
    event.preventDefault();
    event.returnValue = "";
  }
};
onMounted(() => window.addEventListener("beforeunload", unload));
onScopeDispose(() => {
  window.removeEventListener("beforeunload", unload);
  navigationResolve?.(false);
});
watch([() => scope.value.join("|"), id], () => {
  stay();
  for (const mutation of [
    mutations.create,
    mutations.update,
    mutations.position,
    mutations.convert,
    seed,
    catalogSelect,
  ])
    mutation.reset();
  editing.value = false;
  draft.value = emptySaleDraft();
  baseline.value = emptySaleDraft();
  error.value = "";
  notice.value = "";
  conversionOpen.value = false;
  catalogOpen.value = false;
  moveOpen.value = false;
  transferOpen.value = false;
  conversionRequest = null;
  conversionResult.value = null;
  positionUnverified.value = false;
  void nextTick(() => {
    if (record.value?.id === id.value) apply();
  });
});
const contactPreview = useSalesContactPreview(
  computed(() => draft.value.contactId),
  computed(() => editing.value && kind.value === "leads"),
);
</script>
<template>
  <div class="flex min-h-0 min-w-0 flex-col gap-5 overflow-y-auto pb-8">
    <Button variant="ghost" class="self-start" @click="back"
      >← {{ kind === "leads" ? "К лидам" : "К сделкам" }}</Button
    ><SalesFeedback
      :loading="detail.isPending.value"
      :error="
        detail.error.value &&
        (!record || getApiErrorStatus(detail.error.value) === 404)
          ? getApiErrorStatus(detail.error.value) === 404
            ? 'Карточка недоступна или удалена.'
            : getApiErrorMessage(
                detail.error.value,
                'Не удалось выполнить действие.',
              )
          : ''
      "
      @retry="detail.refetch()"
      ><template v-if="record"
        ><header class="flex flex-wrap items-start justify-between gap-4">
          <div class="min-w-0 space-y-2">
            <p class="text-sm text-muted-foreground">
              CRM · {{ kind === "leads" ? "Лид" : "Сделка" }}
            </p>
            <h1
              ref="titleElement"
              tabindex="-1"
              class="break-words text-2xl font-semibold"
            >
              {{ record.title }}
            </h1>
            <div class="flex flex-wrap gap-2">
              <Badge v-if="kind === 'deals'" variant="secondary"
                >Черновик · {{ record.lifecycleState }}</Badge
              ><Badge v-if="frozen">Конвертирован</Badge
              ><Badge variant="outline"
                >{{ funnel.data.value?.name ?? "Воронка" }} ·
                {{
                  funnel.data.value?.stages.find(
                    (s) => s.id === record?.stageId,
                  )?.name ?? "Стадия"
                }}</Badge
              >
            </div>
          </div>
          <div v-if="!frozen" class="flex flex-wrap gap-2">
            <Button
              v-if="!editing"
              :disabled="pending"
              @click="
                apply();
                editing = true;
                notice = '';
              "
              >Редактировать</Button
            ><Button
              variant="outline"
              :disabled="pending || positionUnverified"
              @click="afterClean(() => (moveOpen = true))"
              >Переместить</Button
            ><Button
              variant="outline"
              :disabled="pending || positionUnverified"
              @click="afterClean(() => (transferOpen = true))"
              >Сменить воронку</Button
            ><Button
              v-if="kind === 'leads'"
              :disabled="pending"
              @click="openConversion"
              >Конвертировать</Button
            >
          </div>
        </header>
        <Alert
          v-if="
            detail.isError.value &&
            getApiErrorStatus(detail.error.value) !== 404
          "
          variant="destructive"
          ><AlertDescription
            >Не удалось обновить карточку. Ваш ввод сохранён.
            <Button variant="outline" @click="detail.refetch()"
              >Повторить</Button
            ></AlertDescription
          ></Alert
        ><Alert v-if="error" variant="destructive"
          ><AlertDescription role="alert"
            >{{ error
            }}<Button
              v-if="positionUnverified"
              variant="outline"
              @click="verifyPosition"
              >Проверить положение</Button
            ></AlertDescription
          ></Alert
        ><Alert v-if="notice"
          ><AlertDescription role="status">{{
            notice
          }}</AlertDescription></Alert
        ><Alert
          v-if="people.contacts.isError.value || people.companies.isError.value"
          variant="destructive"
          ><AlertDescription
            >Не удалось загрузить участников.
            <Button
              variant="link"
              @click="
                people.contacts.refetch();
                people.companies.refetch();
              "
              >Повторить</Button
            ></AlertDescription
          ></Alert
        >
        <section
          v-if="record.conversionResult"
          class="space-y-2 rounded-lg border bg-muted/30 p-4"
        >
          <h2 class="font-semibold">Результат конвертации</h2>
          <p>
            {{ new Date(record.conversionResult.convertedAt).toLocaleString() }}
            · {{ record.conversionResult.mode }}
          </p>
          <p class="break-all text-sm text-muted-foreground">
            Инициатор: {{ record.conversionResult.convertedBy }}
          </p>
          <div class="flex flex-wrap gap-2">
            <Button
              v-if="record.conversionResult.contactId"
              variant="link"
              @click="
                router.push(
                  '/crm/contacts/' + record.conversionResult.contactId,
                )
              "
              >Созданный контакт</Button
            ><Button
              v-if="record.conversionResult.companyId"
              variant="link"
              @click="
                router.push(
                  '/crm/companies/' + record.conversionResult.companyId,
                )
              "
              >Созданная компания</Button
            ><Button
              v-if="record.conversionResult.dealId"
              variant="link"
              @click="
                router.push('/crm/deals/' + record.conversionResult.dealId)
              "
              >Созданная сделка</Button
            >
          </div>
          <p class="text-sm">
            Обращение и исходная корзина доступны только для чтения.
          </p>
        </section>
        <form class="flex flex-col gap-6" @submit.prevent="save">
          <section class="rounded-lg border p-4 sm:p-6">
            <h2 class="mb-4 text-lg font-semibold">
              {{
                kind === "leads"
                  ? "Обращение и сведения клиента"
                  : "Сделка и участники"
              }}
            </h2>
            <SaleFields
              v-model="draft"
              :kind="kind"
              :contacts="contacts"
              :contact-preview="contactPreview.data.value"
              :preview-loading="contactPreview.isPending.value"
              :preview-error="contactPreview.isError.value"
              :companies="companies"
              :disabled="!editing || frozen"
              @copy-contact="copyContact"
            />
            <div class="mt-4 flex flex-wrap gap-2">
              <Button
                v-for="contactId in record.contactIds"
                :key="contactId"
                type="button"
                variant="link"
                @click="
                  afterClean(() => router.push('/crm/contacts/' + contactId))
                "
                >{{
                  contacts.find((c) => c.id === contactId)?.label ?? "Контакт"
                }}</Button
              ><Button
                v-for="companyId in record.companyIds"
                :key="companyId"
                type="button"
                variant="link"
                @click="
                  afterClean(() => router.push('/crm/companies/' + companyId))
                "
                >{{
                  companies.find((c) => c.id === companyId)?.label ?? "Компания"
                }}</Button
              >
            </div>
          </section>
          <section class="rounded-lg border p-4 sm:p-6">
            <h2 class="mb-4 text-lg font-semibold">
              Телефоны и email {{ kind === "leads" ? "обращения" : "сделки" }}
            </h2>
            <SalePointsEditor
              v-if="kind === 'leads' && editing && !frozen"
              v-model="draft.points"
              :labels="labels.data.value ?? []"
              :loading="labels.isPending.value"
              :error="labels.isError.value"
              :disabled="!editing || frozen"
            /><template v-else
              ><p
                v-for="point in [
                  ...record.points.phones,
                  ...record.points.emails,
                ]"
                :key="point.bindingId"
                class="text-sm"
              >
                {{ point.value }}
              </p>
              <p
                v-if="
                  !record.points.phones.length && !record.points.emails.length
                "
                class="text-sm text-muted-foreground"
              >
                Точки связи пока не добавлены.
              </p></template
            >
          </section>
          <section class="rounded-lg border p-4 sm:p-6">
            <h2 class="mb-4 text-lg font-semibold">Товары и услуги</h2>
            <BasketEditor
              v-model:items="draft.items"
              v-model:currency="draft.currency"
              :readonly="!editing || frozen"
              :saved-total="record.basket.total"
              :saved-currency="record.basket.currency"
              @catalog="catalogOpen = true"
            />
          </section>
          <section
            v-if="record.sourceLeadId"
            class="space-y-2 rounded-lg border p-4"
          >
            <h2 class="font-semibold">Происхождение из лида</h2>
            <Button
              type="button"
              variant="link"
              @click="
                afterClean(() =>
                  router.push('/crm/leads/' + record?.sourceLeadId),
                )
              "
              >{{
                record.sourceLeadSnapshot?.title ?? "Открыть исходное обращение"
              }}</Button
            >
            <p class="text-sm">
              {{
                [
                  record.sourceLeadSnapshot?.first_name,
                  record.sourceLeadSnapshot?.last_name,
                  record.sourceLeadSnapshot?.company_name,
                ]
                  .filter(Boolean)
                  .join(" · ")
              }}
            </p>
          </section>
          <div
            v-if="editing && !frozen"
            class="sticky bottom-0 flex flex-wrap items-center justify-end gap-3 rounded-lg border bg-background p-4"
          >
            <span class="mr-auto text-sm text-muted-foreground">{{
              dirty ? "Есть несохранённые изменения" : "Изменений нет"
            }}</span
            ><Button
              type="button"
              variant="outline"
              :disabled="pending"
              @click="dirty ? ask(() => (editing = false)) : (editing = false)"
              >Отменить</Button
            ><Button type="submit" :disabled="pending || !dirty">{{
              mutations.update.isPending.value
                ? "Сохраняем…"
                : "Сохранить изменения"
            }}</Button>
          </div>
        </form></template
      ></SalesFeedback
    >
    <CatalogPicker
      v-model:open="catalogOpen"
      v-model:search="catalogInput"
      :items="catalog.data.value ?? []"
      :loading="catalog.isPending.value"
      :error="
        catalog.error.value
          ? getApiErrorMessage(
              catalog.error.value,
              'Не удалось выполнить действие.',
            )
          : ''
      "
      :pending="catalogSelect.isPending.value"
      @select="addCatalog"
      @retry="catalog.refetch()"
    />
    <MoveSaleDialog
      v-model:open="moveOpen"
      :title="record?.title ?? ''"
      :current-id="record?.stageId ?? ''"
      :stages="funnel.data.value?.stages ?? []"
      :funnels="[]"
      :pending="mutations.position.isPending.value"
      @submit="position($event)"
    /><MoveSaleDialog
      v-model:open="transferOpen"
      transfer
      :title="record?.title ?? ''"
      :current-id="record?.funnelId ?? ''"
      :stages="[]"
      :funnels="funnels.data.value?.items ?? []"
      :pending="mutations.position.isPending.value"
      @submit="position($event, true)"
    />
    <UnsavedChangesDialog
      :open="guardOpen"
      :message="guardMessage || undefined"
      :save="!guardMessage"
      :pending="pending"
      @stay="stay"
      @discard="discard"
      @save="saveGuard"
    />
    <ConversionDialog
      v-model:open="conversionOpen"
      :context="conversion.data.value"
      :existing-contact-name="
        contacts.find((c) => c.id === conversion.data.value?.source.contactId)
          ?.label
      "
      :existing-company-name="
        companies.find((c) => c.id === conversion.data.value?.source.companyId)
          ?.label
      "
      :loading="conversion.isPending.value || conversion.isFetching.value"
      :context-error="
        conversion.error.value
          ? getApiErrorMessage(
              conversion.error.value,
              'Не удалось выполнить действие.',
            )
          : ''
      "
      :pending="mutations.convert.isPending.value"
      :error="conversionError"
      :uncertain="uncertain"
      :result="conversionResult"
      :funnels="dealFunnels.data.value?.items ?? []"
      @submit="convert"
      @replay="convert()"
      @return-focus="titleElement?.focus()"
      @check="checkConversion"
      @refresh="refreshConversion"
      @navigate="
        conversionOpen = false;
        router.push($event);
      "
    />
  </div>
</template>
