<script setup lang="ts">
import { computed, nextTick, ref, useId, watch } from "vue";
import { parsePhoneNumberFromString } from "libphonenumber-js/max";
import { Plus, X } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";
import {
  FieldSet,
  FieldLegend,
  FieldGroup,
  Field,
  FieldLabel,
  FieldError,
} from "@/components/ui/field";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import CountrySelect from "./CountrySelect.vue";
import { validateContactPoints } from "../model/validation";
import type {
  ContactPointsFieldProps,
  ContactPointDraft,
  ContactPointKind,
} from "../model/types";
const props = defineProps<
  ContactPointsFieldProps & { kind: ContactPointKind }
>();
const emit = defineEmits<{
  "update:modelValue": [value: ContactPointDraft[]];
  "validation-change": [valid: boolean];
}>();
const id = useId();
const touched = ref(new Set<string>());
const locked = computed(() => props.disabled || props.pending);
const title = computed(() => (props.kind === "phone" ? "Телефоны" : "Email"));
const localErrors = computed(() =>
  validateContactPoints(props.modelValue, props.kind),
);
watch(
  localErrors,
  (errors) => emit("validation-change", Object.keys(errors).length === 0),
  { immediate: true },
);
function errorFor(row: ContactPointDraft) {
  const server = props.errors?.[row.clientKey];
  const local =
    props.attempted || touched.value.has(row.clientKey)
      ? localErrors.value[row.clientKey]
      : undefined;
  return { ...local, ...server };
}
function touch(key: string) {
  touched.value.add(key);
}
function update(row: ContactPointDraft, changes: Partial<ContactPointDraft>) {
  if (locked.value) return;
  emit(
    "update:modelValue",
    props.modelValue.map((item) =>
      item.clientKey === row.clientKey ? { ...item, ...changes } : item,
    ),
  );
}
function setValue(row: ContactPointDraft, value: string | number) {
  const text = String(value);
  const detected =
    props.kind === "phone" && text.trim().startsWith("+")
      ? parsePhoneNumberFromString(text)?.country
      : undefined;
  update(row, { value: text, ...(detected ? { countryCode: detected } : {}) });
}
async function focusRow(key?: string) {
  await nextTick();
  document.getElementById(key ? `${id}-${key}-value` : `${id}-add`)?.focus();
}
async function add() {
  if (locked.value) return;
  const row: ContactPointDraft = {
    clientKey: crypto.randomUUID(),
    value: "",
    labelId: null,
    ...(props.kind === "phone" ? { countryCode: "UA" as const } : {}),
  };
  emit("update:modelValue", [...props.modelValue, row]);
  await focusRow(row.clientKey);
}
async function remove(row: ContactPointDraft) {
  if (locked.value) return;
  const index = props.modelValue.findIndex(
    (item) => item.clientKey === row.clientKey,
  );
  const remaining = props.modelValue.filter(
    (item) => item.clientKey !== row.clientKey,
  );
  emit("update:modelValue", remaining);
  await focusRow(remaining[Math.min(index, remaining.length - 1)]?.clientKey);
}
function labelOptions(row: ContactPointDraft) {
  return props.labels.filter(
    (label) =>
      label.type === props.kind && (label.isActive || label.id === row.labelId),
  );
}
function labelText(row: ContactPointDraft) {
  if (!row.labelId) return "Без подписи";
  const label = props.labels.find((item) => item.id === row.labelId);
  if (!label) return props.labelsLoading ? "Загрузка…" : "Подпись недоступна";
  return label.name + (label.isActive ? "" : " (архив)");
}
</script>
<template>
  <FieldSet class="min-w-0 gap-3" :aria-label="title">
    <FieldLegend variant="label">{{ title }}</FieldLegend>
    <FieldGroup class="gap-3">
      <div
        v-for="(row, index) in modelValue"
        :key="row.clientKey"
        class="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-start gap-2 sm:grid-cols-[minmax(0,1fr)_10rem_auto]"
      >
        <Field
          class="col-span-2 min-w-0 sm:col-span-1"
          :data-invalid="
            Boolean(
              errorFor(row).value ||
              errorFor(row).countryCode ||
              errorFor(row).bindingId,
            ) || undefined
          "
          :data-disabled="locked || undefined"
        >
          <FieldLabel class="sr-only" :for="`${id}-${row.clientKey}-value`"
            >{{ kind === "phone" ? "Телефон" : "Email" }}
            {{ index + 1 }}</FieldLabel
          >
          <InputGroup v-if="kind === 'phone'">
            <InputGroupAddon>
              <CountrySelect
                :id="`${id}-${row.clientKey}-country`"
                :model-value="row.countryCode"
                :disabled="locked"
                :invalid="Boolean(errorFor(row).countryCode)"
                :described-by="`${id}-${row.clientKey}-error`"
                @update:model-value="
                  update(row, { countryCode: $event });
                  touch(row.clientKey);
                "
              />
            </InputGroupAddon>
            <InputGroupInput
              :id="`${id}-${row.clientKey}-value`"
              type="tel"
              autocomplete="tel"
              placeholder="050 123 45 67"
              :model-value="row.value"
              :disabled="locked"
              :aria-invalid="Boolean(errorFor(row).value)"
              :aria-describedby="`${id}-${row.clientKey}-error`"
              @update:model-value="setValue(row, $event)"
              @blur="touch(row.clientKey)"
            />
          </InputGroup>
          <Input
            v-else
            :id="`${id}-${row.clientKey}-value`"
            type="email"
            autocomplete="email"
            placeholder="name@domain.com"
            :model-value="row.value"
            :disabled="locked"
            :aria-invalid="Boolean(errorFor(row).value)"
            :aria-describedby="`${id}-${row.clientKey}-error`"
            @update:model-value="setValue(row, $event)"
            @blur="touch(row.clientKey)"
          />
          <FieldError
            v-if="
              errorFor(row).value ||
              errorFor(row).countryCode ||
              errorFor(row).bindingId
            "
            :id="`${id}-${row.clientKey}-error`"
            :errors="[
              errorFor(row).value,
              errorFor(row).countryCode,
              errorFor(row).bindingId,
            ]"
          />
        </Field>
        <Field
          class="min-w-0"
          :data-invalid="Boolean(errorFor(row).labelId) || undefined"
        >
          <FieldLabel class="sr-only" :for="`${id}-${row.clientKey}-label`"
            >Подпись {{ kind === "phone" ? "телефона" : "email" }}
            {{ index + 1 }}</FieldLabel
          >
          <Select
            :model-value="row.labelId ?? '_none'"
            :disabled="locked || labelsLoading || labelsError"
            @update:model-value="
              update(row, {
                labelId: $event === '_none' ? null : String($event),
              })
            "
          >
            <SelectTrigger
              :id="`${id}-${row.clientKey}-label`"
              class="w-full"
              :aria-invalid="Boolean(errorFor(row).labelId)"
              :aria-describedby="`${id}-${row.clientKey}-label-error`"
              ><SelectValue>{{ labelText(row) }}</SelectValue></SelectTrigger
            >
            <SelectContent
              ><SelectGroup>
                <SelectItem value="_none">Без подписи</SelectItem>
                <SelectItem
                  v-if="
                    row.labelId &&
                    !labelOptions(row).some((label) => label.id === row.labelId)
                  "
                  :value="row.labelId"
                  disabled
                  >Подпись недоступна</SelectItem
                >
                <SelectItem
                  v-for="label in labelOptions(row)"
                  :key="label.id"
                  :value="label.id"
                  :disabled="!label.isActive"
                  >{{ label.name
                  }}{{ label.isActive ? "" : " (архив)" }}</SelectItem
                >
              </SelectGroup></SelectContent
            >
          </Select>
          <FieldError
            v-if="errorFor(row).labelId"
            :id="`${id}-${row.clientKey}-label-error`"
            :errors="[errorFor(row).labelId]"
          />
        </Field>
        <Tooltip
          ><TooltipTrigger as-child>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              :disabled="locked"
              :aria-label="`Удалить ${kind === 'phone' ? 'телефон' : 'email'} ${index + 1}`"
              @click="remove(row)"
              ><X
            /></Button> </TooltipTrigger
          ><TooltipContent>Удалить связь</TooltipContent></Tooltip
        >
      </div>
    </FieldGroup>
    <Button
      :id="`${id}-add`"
      type="button"
      variant="outline"
      size="sm"
      class="self-start"
      :disabled="locked"
      @click="add"
      ><Plus data-icon="inline-start" />{{
        kind === "phone" ? "Добавить телефон" : "Добавить email"
      }}</Button
    >
  </FieldSet>
</template>
