<script setup lang="ts">
import { useId } from "vue";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
import { Field, FieldLabel, FieldGroup } from "@/components/ui/field";
import PeoplePicker from "./PeoplePicker.vue";
import type { SaleDraft, SalesKind } from "../../model/sales.types";
import type { Funnel } from "@/modules/funnel";
const props = defineProps<{
  kind: SalesKind;
  modelValue: SaleDraft;
  funnels?: Funnel[];
  contacts: { id: string; label: string }[];
  companies: { id: string; label: string }[];
  creating?: boolean;
  disabled?: boolean;
  contactPreview?: { name: string; values: string[] };
  previewLoading?: boolean;
  previewError?: boolean;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: SaleDraft];
  copyContact: [id: string];
}>();
const uid = useId();
function change<K extends keyof SaleDraft>(key: K, value: SaleDraft[K]) {
  emit("update:modelValue", { ...props.modelValue, [key]: value });
}
</script>
<template>
  <FieldGroup
    ><Field
      ><FieldLabel :for="uid + 'title'"
        >Название {{ kind === "leads" ? "обращения" : "сделки" }} *</FieldLabel
      ><Input
        :id="uid + 'title'"
        :model-value="modelValue.title"
        maxlength="255"
        required
        :disabled="disabled"
        @update:model-value="change('title', String($event))" /></Field
    ><template v-if="creating"
      ><Field
        ><FieldLabel :for="uid + 'currency'">Валюта *</FieldLabel
        ><NativeSelect
          :id="uid + 'currency'"
          :model-value="modelValue.currency"
          :disabled="disabled"
          required
          @update:model-value="change('currency', String($event))"
          ><option value="" disabled>Выберите валюту</option>
          <option>USD</option>
          <option>EUR</option>
          <option>UAH</option></NativeSelect
        ></Field
      ><Field
        ><FieldLabel :for="uid + 'funnel'">Воронка</FieldLabel
        ><NativeSelect
          :id="uid + 'funnel'"
          :model-value="modelValue.funnelId"
          :disabled="disabled"
          @update:model-value="change('funnelId', String($event))"
          ><option value="">По умолчанию</option>
          <option v-for="f in funnels" :key="f.id" :value="f.id">
            {{ f.name }}
          </option></NativeSelect
        ></Field
      ></template
    ><template v-if="kind === 'leads'"
      ><Field
        ><FieldLabel :for="uid + 'contact'"
          >Существующий контакт — необязательно</FieldLabel
        ><NativeSelect
          :id="uid + 'contact'"
          :model-value="modelValue.contactId ?? ''"
          :disabled="disabled"
          @update:model-value="change('contactId', String($event) || null)"
          ><option value="">Ручные данные</option>
          <option v-for="c in contacts" :key="c.id" :value="c.id">
            {{ c.label }}
          </option></NativeSelect
        >
        <div
          v-if="modelValue.contactId && (creating || !disabled)"
          class="space-y-1 rounded-md bg-muted p-3 text-sm"
          aria-live="polite"
        >
          <p class="font-medium">Данные выбранного контакта для копирования</p>
          <p v-if="previewLoading">Загрузка…</p>
          <p v-else-if="previewError" class="text-destructive">
            Не удалось загрузить сведения. Кнопка копирования повторит запрос.
          </p>
          <template v-else-if="contactPreview"
            ><p>{{ contactPreview.name }}</p>
            <p v-for="value in contactPreview.values" :key="value">
              {{ value }}
            </p>
            <p
              v-if="!contactPreview.values.length"
              class="text-muted-foreground"
            >
              Телефоны и email не указаны.
            </p></template
          >
        </div>
        <Button
          v-if="modelValue.contactId && (creating || !disabled)"
          type="button"
          variant="outline"
          :disabled="disabled"
          @click="emit('copyContact', modelValue.contactId)"
          >Скопировать ФИО, телефоны и email</Button
        ></Field
      >
      <div class="grid gap-4 sm:grid-cols-2">
        <Field
          v-for="entry in [
            ['lastName', 'Фамилия'],
            ['firstName', 'Имя'],
            ['middleName', 'Отчество'],
            ['companyName', 'Компания — текст'],
          ] as const"
          :key="entry[0]"
          ><FieldLabel :for="uid + entry[0]">{{ entry[1] }}</FieldLabel
          ><Input
            :id="uid + entry[0]"
            :model-value="modelValue[entry[0]]"
            maxlength="255"
            :disabled="disabled"
            @update:model-value="change(entry[0], String($event))"
        /></Field>
      </div>
      <Field
        ><FieldLabel :for="uid + 'company'"
          >Связь с существующей компанией</FieldLabel
        ><NativeSelect
          :id="uid + 'company'"
          :model-value="modelValue.companyId ?? ''"
          :disabled="disabled"
          @update:model-value="change('companyId', String($event) || null)"
          ><option value="">Не выбрана</option>
          <option v-for="c in companies" :key="c.id" :value="c.id">
            {{ c.label }}
          </option></NativeSelect
        ></Field
      >
      <p class="text-sm text-muted-foreground">
        ФИО и точки связи принадлежат обращению. Правки не меняют исходный
        контакт.
      </p></template
    ><template v-else
      ><PeoplePicker
        label="Контакты — участники"
        :options="contacts"
        :model-value="modelValue.contactIds"
        :disabled="disabled"
        @update:model-value="change('contactIds', $event)" /><PeoplePicker
        label="Компании — участники"
        :options="companies"
        :model-value="modelValue.companyIds"
        :disabled="disabled"
        @update:model-value="change('companyIds', $event)" /></template
  ></FieldGroup>
</template>
