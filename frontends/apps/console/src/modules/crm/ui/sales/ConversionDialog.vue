<script setup lang="ts">
import { computed, ref, watch, useId } from "vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FieldLabel } from "@/components/ui/field";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { Funnel } from "@/modules/funnel";
import type {
  ConversionContext,
  ConversionDraft,
  ConversionMode,
  ConversionResult,
  ConversionSubmission,
} from "../../model/sales.types";
import BasketEditor from "../basket/BasketEditor.vue";
import SalesFeedback from "./SalesFeedback.vue";
import PeoplePicker from "./PeoplePicker.vue";
const props = defineProps<{
  open: boolean;
  context?: ConversionContext;
  loading: boolean;
  contextError: string;
  pending: boolean;
  error: string;
  uncertain: boolean;
  result: ConversionResult | null;
  funnels: Funnel[];
  existingContactName?: string;
  existingCompanyName?: string;
}>();
const emit = defineEmits<{
  "update:open": [open: boolean];
  submit: [submission: ConversionSubmission];
  refresh: [];
  check: [];
  replay: [];
  navigate: [path: string];
  returnFocus: [];
}>();
const uid = useId();
const modeNames: Record<ConversionMode, string> = {
  contact: "Контакт",
  company: "Компания",
  contact_company: "Контакт + компания",
  contact_deal: "Контакт + сделка",
  company_deal: "Компания + сделка",
  contact_company_deal: "Контакт + компания + сделка",
  deal: "Только сделка",
};
const empty = (): ConversionDraft => ({
  mode: "",
  firstName: "",
  lastName: "",
  middleName: "",
  legalName: "",
  title: "",
  funnelId: "",
  additionalCompanyIds: [],
  contactPoints: [],
  companyPoints: [],
  dealPoints: [],
  links: [],
});
const draft = ref(empty()),
  attempted = ref(false),
  initialized = ref(false),
  linkContactToSource = ref(false),
  linkCompanyToSource = ref(false),
  extraLinks = ref<string[]>([]);
const creates = computed(() => new Set(draft.value.mode.split("_"))),
  source = computed(() => props.context?.source),
  points = computed(() =>
    [
      ...(source.value?.points.phones ?? []),
      ...(source.value?.points.emails ?? []),
    ].filter((p) => !!p.bindingId),
  );
watch(
  () => props.open,
  (open) => {
    if (open) {
      initialized.value = false;
      attempted.value = false;
      draft.value = empty();
      linkContactToSource.value = false;
      linkCompanyToSource.value = false;
      extraLinks.value = [];
    }
  },
  { flush: "sync" },
);
watch(
  () => [props.open, props.context] as const,
  ([, context]) => {
    if (!context || !props.open) return;
    const ids = points.value.map((p) => p.bindingId!);
    if (!initialized.value) {
      draft.value = {
        ...empty(),
        firstName: context.source.firstName ?? "",
        lastName: context.source.lastName ?? "",
        middleName: context.source.middleName ?? "",
        legalName: context.source.companyName ?? "",
        title: context.source.title,
        funnelId: props.funnels.find((f) => f.isDefault)?.id ?? "",
        contactPoints: [...ids],
        dealPoints: [...ids],
      };
      initialized.value = true;
    } else {
      for (const k of ["contactPoints", "companyPoints", "dealPoints"] as const)
        draft.value[k] = draft.value[k].filter((id) => ids.includes(id));
      draft.value.additionalCompanyIds =
        draft.value.additionalCompanyIds.filter((id) =>
          context.availableCompanies.some((c) => c.id === id),
        );
    }
  },
  { immediate: true },
);
watch(
  () => props.funnels,
  (items) => {
    if (!draft.value.funnelId)
      draft.value.funnelId = items.find((f) => f.isDefault)?.id ?? "";
  },
);
function toggle(
  k: "contactPoints" | "companyPoints" | "dealPoints",
  id: string,
  checked: unknown,
) {
  draft.value[k] = checked
    ? [...draft.value[k].filter((v) => v !== id), id]
    : draft.value[k].filter((v) => v !== id);
}
const invalid = computed(() =>
  !draft.value.mode
    ? "Выберите режим конвертации."
    : creates.value.has("contact") && !draft.value.firstName.trim()
      ? "Укажите имя нового контакта."
      : creates.value.has("company") && !draft.value.legalName.trim()
        ? "Укажите название новой компании."
        : creates.value.has("deal") &&
            (!draft.value.title.trim() || !draft.value.funnelId)
          ? "Укажите название и воронку новой сделки."
          : "",
);
const links = computed(() => {
  const value: { contactId: string | null; companyId: string | null }[] = [];
  if (
    creates.value.has("contact") &&
    source.value?.companyId &&
    linkContactToSource.value
  )
    value.push({ contactId: null, companyId: source.value.companyId });
  if (
    creates.value.has("company") &&
    source.value?.contactId &&
    linkCompanyToSource.value
  )
    value.push({ contactId: source.value.contactId, companyId: null });
  if (creates.value.has("contact") && creates.value.has("deal"))
    for (const id of extraLinks.value.filter((id) =>
      draft.value.additionalCompanyIds.includes(id),
    ))
      value.push({ contactId: null, companyId: id });
  return value;
});
function pointValues(
  kind: "contactPoints" | "companyPoints" | "dealPoints",
): string {
  return (
    points.value
      .filter((point) => draft.value[kind].includes(point.bindingId!))
      .map((point) => point.value)
      .join(" · ") || "не выбраны"
  );
}
const newContactName = computed(() =>
  [draft.value.firstName, draft.value.lastName].filter(Boolean).join(" "),
);
function companyLabel(id: string | null): string {
  if (!id) return draft.value.legalName + " (новая)";
  if (id === source.value?.companyId)
    return (props.existingCompanyName ?? id) + " (существующая)";
  return (
    (props.context?.availableCompanies.find((c) => c.id === id)?.legalName ??
      id) + " (существующая)"
  );
}
const participantsSummary = computed(() => {
  if (!creates.value.has("deal")) return [];
  const values: string[] = [];
  if (source.value?.contactId)
    values.push(
      "Контакт: " +
        (props.existingContactName ?? source.value.contactId) +
        " (существующий)",
    );
  if (creates.value.has("contact"))
    values.push("Контакт: " + newContactName.value + " (новый)");
  if (source.value?.companyId)
    values.push("Компания: " + companyLabel(source.value.companyId));
  if (creates.value.has("company"))
    values.push("Компания: " + companyLabel(null));
  for (const id of draft.value.additionalCompanyIds)
    if (id !== source.value?.companyId)
      values.push("Компания: " + companyLabel(id));
  return values;
});
const linksSummary = computed(() => {
  const values = links.value.map(
    (link) =>
      (link.contactId
        ? (props.existingContactName ?? link.contactId) + " (существующий)"
        : newContactName.value + " (новый)") +
      " → " +
      companyLabel(link.companyId),
  );
  if (creates.value.has("contact") && creates.value.has("company"))
    values.unshift(newContactName.value + " (новый) → " + companyLabel(null));
  return values;
});
function submit() {
  attempted.value = true;
  if (invalid.value || !props.context || !draft.value.mode) return;
  const d = draft.value;
  emit("submit", {
    mode: d.mode as ConversionMode,
    expectedSourceToken: props.context.sourceToken,
    expectedBasketRevision: props.context.source.basket.revision,
    ...(creates.value.has("contact")
      ? {
          contact: {
            firstName: d.firstName,
            lastName: d.lastName || null,
            middleName: d.middleName || null,
          },
          contactPoints: d.contactPoints,
        }
      : {}),
    ...(creates.value.has("company")
      ? { company: { legalName: d.legalName }, companyPoints: d.companyPoints }
      : {}),
    ...(creates.value.has("deal")
      ? {
          deal: {
            title: d.title,
            funnelId: d.funnelId,
            additionalCompanyIds: d.additionalCompanyIds,
          },
          dealPoints: d.dealPoints,
        }
      : {}),
    links: links.value,
  });
}
</script>
<template>
  <Dialog :open="open" @update:open="!pending && emit('update:open', $event)"
    ><DialogContent
      class="h-dvh max-h-dvh max-w-full overflow-y-auto rounded-none sm:h-auto sm:max-h-[90dvh] sm:max-w-4xl sm:rounded-lg"
      :show-close-button="!pending"
      @close-auto-focus="
        result && ($event.preventDefault(), emit('returnFocus'))
      "
      @escape-key-down="pending && $event.preventDefault()"
      @interact-outside="pending && $event.preventDefault()"
      ><DialogHeader
        ><DialogTitle>{{
          result ? "Лид конвертирован" : "Конвертация лида"
        }}</DialogTitle
        ><DialogDescription>{{
          result
            ? "Результаты сохранены. Исходное обращение и его корзина доступны для чтения."
            : "Проверьте новые записи, точки связи и состав продажи перед подтверждением."
        }}</DialogDescription></DialogHeader
      >
      <div v-if="result" class="flex flex-col gap-4">
        <p>Режим: {{ modeNames[result.mode] }}</p>
        <p>Дата: {{ new Date(result.convertedAt).toLocaleString() }}</p>
        <p>Инициатор: {{ result.convertedBy }}</p>
        <Button
          v-if="result.contactId"
          variant="outline"
          @click="emit('navigate', '/crm/contacts/' + result.contactId)"
          >Открыть новый контакт</Button
        ><Button
          v-if="result.companyId"
          variant="outline"
          @click="emit('navigate', '/crm/companies/' + result.companyId)"
          >Открыть новую компанию</Button
        ><Button
          v-if="result.dealId"
          @click="emit('navigate', '/crm/deals/' + result.dealId)"
          >Открыть новую сделку</Button
        >
        <p>
          {{
            result.dealId
              ? "Сделка получила независимую копию корзины."
              : "Корзина осталась у исходного лида."
          }}
        </p>
        <Button variant="secondary" @click="emit('update:open', false)"
          >Вернуться к лиду</Button
        >
      </div>
      <SalesFeedback
        v-else
        :loading="loading"
        :error="contextError"
        @retry="emit('refresh')"
        ><form class="flex flex-col gap-6" @submit.prevent="submit">
          <div v-if="source" class="space-y-1 rounded-md bg-muted p-3 text-sm">
            <p class="font-medium">Источник: {{ source.title }}</p>
            <p>
              {{
                [source.firstName, source.lastName, source.companyName]
                  .filter(Boolean)
                  .join(" · ") || "Сведения о клиенте не указаны"
              }}
            </p>
          </div>
          <fieldset
            :disabled="pending || uncertain"
            class="flex min-w-0 flex-col gap-6 disabled:opacity-70"
          >
            <section class="space-y-3">
              <h2 class="font-semibold">1. Что создать</h2>
              <div class="grid gap-2 sm:grid-cols-2">
                <label
                  v-for="mode in context?.modes ?? []"
                  :key="mode"
                  class="flex items-center gap-3 rounded-md border p-3"
                  ><input
                    v-model="draft.mode"
                    type="radio"
                    :value="mode"
                    :name="uid + 'mode'"
                    required
                    class="size-4 accent-primary"
                  />{{ modeNames[mode] }}</label
                >
              </div>
            </section>
            <section v-if="draft.mode" class="space-y-4">
              <h2 class="font-semibold">2. Данные новых объектов</h2>
              <div
                v-if="creates.has('contact')"
                class="space-y-3 rounded-md border p-4"
              >
                <h3 class="font-medium">Новый контакт</h3>
                <Field
                  v-for="entry in [
                    ['firstName', 'Имя *'],
                    ['lastName', 'Фамилия'],
                    ['middleName', 'Отчество'],
                  ] as const"
                  :key="entry[0]"
                  ><FieldLabel :for="uid + entry[0]">{{ entry[1] }}</FieldLabel
                  ><Input
                    :id="uid + entry[0]"
                    v-model="draft[entry[0]]"
                    :required="entry[0] === 'firstName'"
                    maxlength="255"
                /></Field>
              </div>
              <Field v-if="creates.has('company')"
                ><FieldLabel :for="uid + 'company'"
                  >Название новой компании *</FieldLabel
                ><Input
                  :id="uid + 'company'"
                  v-model="draft.legalName"
                  required
                  maxlength="255" /></Field
              ><Field v-if="creates.has('deal')"
                ><FieldLabel :for="uid + 'deal'"
                  >Название новой сделки *</FieldLabel
                ><Input
                  :id="uid + 'deal'"
                  v-model="draft.title"
                  required
                  maxlength="255"
              /></Field>
            </section>
            <section v-if="draft.mode" class="space-y-3">
              <h2 class="font-semibold">3. Участники и связи</h2>
              <div class="rounded-md bg-muted p-3 text-sm">
                <p>Существующие записи сохраняются без изменений.</p>
                <p v-if="source?.contactId">
                  Существующий контакт:
                  {{ existingContactName ?? source.contactId }}.
                  {{
                    creates.has("deal")
                      ? "Станет участником новой сделки."
                      : "Запись останется без изменений."
                  }}
                </p>
                <p v-if="source?.companyId">
                  Существующая компания:
                  {{ existingCompanyName ?? source.companyId }}.
                  {{
                    creates.has("deal")
                      ? "Станет участником новой сделки."
                      : "Запись останется без изменений."
                  }}
                </p>
                <p v-if="creates.has('contact') && creates.has('company')">
                  Между новым контактом и новой компанией будет создана связь.
                </p>
                <p v-if="creates.has('deal')">
                  Новые контакт и компания также станут участниками сделки, если
                  выбраны в режиме.
                </p>
              </div>
              <PeoplePicker
                v-if="creates.has('deal')"
                v-model="draft.additionalCompanyIds"
                label="Дополнительные компании исходного контакта — участники сделки"
                :options="
                  (context?.availableCompanies ?? [])
                    .filter((c) => c.id !== source?.companyId)
                    .map((c) => ({ id: c.id, label: c.legalName }))
                "
              /><label
                v-if="creates.has('contact') && source?.companyId"
                class="flex items-center gap-2 text-sm"
                ><Checkbox v-model="linkContactToSource" />Связать новый контакт
                с компанией обращения</label
              ><label
                v-if="creates.has('company') && source?.contactId"
                class="flex items-center gap-2 text-sm"
                ><Checkbox v-model="linkCompanyToSource" />Связать контакт
                обращения с новой компанией</label
              ><PeoplePicker
                v-if="
                  creates.has('contact') &&
                  creates.has('deal') &&
                  draft.additionalCompanyIds.length
                "
                v-model="extraLinks"
                label="Отдельные связи нового контакта с дополнительными компаниями"
                :options="
                  (context?.availableCompanies ?? [])
                    .filter((c) => draft.additionalCompanyIds.includes(c.id))
                    .map((c) => ({ id: c.id, label: c.legalName }))
                "
              />
            </section>
            <section v-if="draft.mode" class="space-y-4">
              <h2 class="font-semibold">4. Телефоны и email новых объектов</h2>
              <p class="text-sm text-muted-foreground">
                Точки связи копируются независимо. Для компании первоначально
                ничего не выбрано.
              </p>
              <template
                v-for="entry in [
                  ['contact', 'contactPoints', 'Контакт'],
                  ['company', 'companyPoints', 'Компания'],
                  ['deal', 'dealPoints', 'Сделка'],
                ] as const"
                :key="entry[0]"
                ><fieldset
                  v-if="creates.has(entry[0])"
                  class="space-y-2 rounded-md border p-3"
                >
                  <legend class="px-1 text-sm font-medium">
                    {{ entry[2] }}
                  </legend>
                  <label
                    v-for="p in points"
                    :key="p.bindingId"
                    class="flex items-center gap-2 text-sm"
                    ><Checkbox
                      :model-value="draft[entry[1]].includes(p.bindingId!)"
                      @update:model-value="
                        toggle(entry[1], p.bindingId!, $event)
                      "
                    />{{ p.value }}</label
                  >
                  <p
                    v-if="!points.length"
                    class="text-sm text-muted-foreground"
                  >
                    У лида нет телефонов и email.
                  </p>
                </fieldset></template
              >
            </section>
            <section v-if="draft.mode && source" class="space-y-3">
              <h2 class="font-semibold">5. Корзина и воронка</h2>
              <p class="text-sm text-muted-foreground">
                {{
                  creates.has("deal")
                    ? "Корзина будет скопирована в новую сделку. Суммы и строки здесь не изменяются."
                    : "Новая сделка не создаётся. Корзина останется у лида и станет доступна только для чтения."
                }}
              </p>
              <Field v-if="creates.has('deal')"
                ><FieldLabel :for="uid + 'funnel'"
                  >Воронка новой сделки *</FieldLabel
                ><NativeSelect
                  :id="uid + 'funnel'"
                  v-model="draft.funnelId"
                  required
                  ><option value="" disabled>Выберите</option>
                  <option v-for="f in funnels" :key="f.id" :value="f.id">
                    {{ f.name }} → {{ f.stages[0]?.name }}
                  </option></NativeSelect
                ></Field
              ><BasketEditor
                :items="source.basket.items"
                :currency="source.basket.currency"
                readonly
              />
            </section>
            <section v-if="draft.mode" class="space-y-2 rounded-md border p-4">
              <h2 class="font-semibold">6. Проверьте итог</h2>
              <p>Будут созданы: {{ modeNames[draft.mode] }}.</p>
              <p v-if="creates.has('contact')">
                Контакт: {{ draft.firstName }} {{ draft.lastName }} · точек
                связи: {{ draft.contactPoints.length }}. Точки связи:
                {{ pointValues("contactPoints") }}
              </p>
              <p v-if="creates.has('company')">
                Компания: {{ draft.legalName }} · точек связи:
                {{ draft.companyPoints.length }}. Точки связи:
                {{ pointValues("companyPoints") }}
              </p>
              <p v-if="creates.has('deal')">
                Сделка: {{ draft.title }} · точек связи:
                {{ draft.dealPoints.length }}. Точки связи:
                {{ pointValues("dealPoints") }} · {{ source?.basket.total }}
                {{ source?.basket.currency }}
              </p>
              <div v-if="creates.has('deal')" class="space-y-1">
                <p class="font-medium">Участники новой сделки</p>
                <ul
                  v-if="participantsSummary.length"
                  class="list-inside list-disc"
                >
                  <li
                    v-for="participant in participantsSummary"
                    :key="participant"
                  >
                    {{ participant }}
                  </li>
                </ul>
                <p v-else>Участники не выбраны.</p>
              </div>
              <ul v-if="linksSummary.length" class="list-inside list-disc">
                <li v-for="link in linksSummary" :key="link">
                  Связь: {{ link }}
                </li>
              </ul>
              <p>
                Связей Contact–Company:
                {{
                  links.length +
                  (creates.has("contact") && creates.has("company") ? 1 : 0)
                }}.
              </p>
              <p class="text-sm text-muted-foreground">
                После конвертации исходный лид и его корзина доступны только для
                чтения.
              </p>
            </section>
          </fieldset>
          <Alert v-if="error || (attempted && invalid)" variant="destructive"
            ><AlertDescription role="alert">{{
              error || invalid
            }}</AlertDescription></Alert
          >
          <div v-if="uncertain" class="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              :disabled="pending"
              @click="emit('check')"
              >Проверить результат</Button
            ><Button type="button" :disabled="pending" @click="emit('replay')"
              >Повторить безопасно с тем же ключом</Button
            >
          </div>
          <DialogFooter
            ><Button
              type="button"
              variant="outline"
              :disabled="pending"
              @click="emit('update:open', false)"
              >Закрыть</Button
            ><Button
              v-if="!uncertain"
              type="submit"
              :disabled="pending || !draft.mode"
              >{{ pending ? "Конвертируем…" : "Конвертировать" }}</Button
            ></DialogFooter
          ><Button
            v-if="error && !uncertain"
            type="button"
            variant="ghost"
            :disabled="pending"
            @click="emit('refresh')"
            >Обновить контекст и проверить выбор</Button
          >
        </form></SalesFeedback
      ></DialogContent
    ></Dialog
  >
</template>
