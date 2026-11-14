<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldError,
  FieldDescription,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type {
  StockLotValues,
  StockLotErrors,
} from "../../model/stock-lot.types";
const props = defineProps<{
  open: boolean;
  sku: string;
  values: StockLotValues;
  errors: StockLotErrors;
  pending: boolean;
  disabled: boolean;
  uncertain: boolean;
  error: string;
  expirationMode: string;
}>();
const emit = defineEmits<{
  close: [];
  change: [values: StockLotValues];
  submit: [];
  check: [];
  refresh: [];
}>();
function change(key: keyof StockLotValues, value: string | number): void {
  emit("change", { ...props.values, [key]: String(value) });
}
function commitDate(key: "manufacturedOn" | "expiresOn", event: Event): void {
  // Календарь может подтвердить значение через change без текстового input.
  if (event.target instanceof HTMLInputElement) change(key, event.target.value);
}
</script>
<template>
  <Dialog :open="open" @update:open="!$event && !pending && emit('close')"
    ><DialogContent
      class="max-h-[calc(100dvh-2rem)] overflow-y-auto"
      :show-close-button="!pending"
      @escape-key-down="pending && $event.preventDefault()"
      @interact-outside="pending && $event.preventDefault()"
    >
      <DialogHeader
        ><DialogTitle>Создать партию</DialogTitle
        ><DialogDescription class="break-all"
          >SKU: {{ sku }}. Укажите номер; даты при создании
          необязательны.</DialogDescription
        ></DialogHeader
      >
      <form
        class="flex flex-col gap-4"
        novalidate
        :aria-busy="pending"
        @submit.prevent="emit('submit')"
      >
        <FieldGroup>
          <Field :data-invalid="!!errors.number"
            ><FieldLabel for="lot-number">Номер партии</FieldLabel
            ><Input
              id="lot-number"
              :model-value="values.number"
              :disabled="pending || disabled || uncertain"
              :aria-invalid="!!errors.number"
              aria-describedby="lot-number-hint lot-number-error"
              autocomplete="off"
              autocapitalize="none"
              spellcheck="false"
              @update:model-value="change('number', $event)" /><FieldDescription
              id="lot-number-hint"
              >Регистр и ведущие нули сохраняются.</FieldDescription
            ><FieldError id="lot-number-error" :errors="[errors.number]"
          /></Field>
          <Field :data-invalid="!!errors.manufacturedOn"
            ><FieldLabel for="lot-manufactured">Дата производства</FieldLabel
            ><Input
              id="lot-manufactured"
              type="date"
              min="0001-01-01"
              max="9999-12-31"
              :model-value="values.manufacturedOn"
              :disabled="pending || disabled || uncertain"
              :aria-invalid="!!errors.manufacturedOn"
              aria-describedby="lot-manufactured-error"
              @change="commitDate('manufacturedOn', $event)"
              @update:model-value="
                change('manufacturedOn', $event)
              " /><FieldError
              id="lot-manufactured-error"
              :errors="[errors.manufacturedOn]"
          /></Field>
          <Field :data-invalid="!!errors.expiresOn"
            ><FieldLabel for="lot-expires">Срок годности</FieldLabel
            ><Input
              id="lot-expires"
              type="date"
              min="0001-01-01"
              max="9999-12-31"
              :model-value="values.expiresOn"
              :disabled="
                pending || disabled || uncertain || expirationMode === 'NONE'
              "
              :aria-invalid="!!errors.expiresOn"
              aria-describedby="lot-expires-hint lot-expires-error"
              @change="commitDate('expiresOn', $event)"
              @update:model-value="change('expiresOn', $event)"
            /><FieldDescription id="lot-expires-hint">{{
              expirationMode === "NONE"
                ? "В настройках SKU срок годности отключён."
                : expirationMode === "REQUIRED"
                  ? "Срок понадобится перед поступлением. Сейчас поле необязательно."
                  : "Необязательная дата-заметка."
            }}</FieldDescription
            ><FieldError
              id="lot-expires-error"
              :errors="[errors.expiresOn]"
            /><Button
              v-if="expirationMode === 'NONE' && values.expiresOn"
              type="button"
              variant="link"
              :disabled="pending || uncertain"
              @click="change('expiresOn', '')"
              >Очистить срок</Button
            ></Field
          >
        </FieldGroup>
        <Alert v-if="error" variant="destructive"
          ><AlertDescription>{{ error }}</AlertDescription></Alert
        >
        <Button
          v-if="disabled"
          type="button"
          variant="outline"
          :disabled="pending"
          @click="emit('refresh')"
          >Обновить настройки SKU</Button
        >
        <DialogFooter class="flex-wrap gap-2"
          ><Button
            type="button"
            variant="outline"
            :disabled="pending"
            @click="emit('close')"
            >Отмена</Button
          ><Button
            v-if="uncertain"
            type="button"
            :disabled="pending || disabled"
            @click="emit('check')"
            >Проверить список</Button
          ><Button v-else type="submit" :disabled="pending || disabled">{{
            pending ? "Создание…" : "Создать"
          }}</Button></DialogFooter
        >
      </form>
    </DialogContent></Dialog
  >
</template>
