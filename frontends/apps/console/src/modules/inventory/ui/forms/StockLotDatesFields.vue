<script setup lang="ts">
import {
  Field,
  FieldLabel,
  FieldError,
  FieldDescription,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type {
  StockLotDatesValues,
  StockLotDatesErrors,
} from "../../model/stock-lot.types";
const props = withDefaults(
  defineProps<{
    values: StockLotDatesValues;
    errors: StockLotDatesErrors;
    disabled: boolean;
    expirationMode: string;
    idPrefix?: string;
  }>(),
  { idPrefix: "lot" },
);
const emit = defineEmits<{ change: [values: StockLotDatesValues] }>();
function change(key: keyof StockLotDatesValues, value: string | number): void {
  emit("change", {
    manufacturedOn: props.values.manufacturedOn,
    expiresOn: props.values.expiresOn,
    [key]: String(value),
  });
}
function commitDate(key: keyof StockLotDatesValues, event: Event): void {
  // Календарь может подтвердить значение через change без текстового input.
  if (event.target instanceof HTMLInputElement) change(key, event.target.value);
}
</script>
<template>
  <Field :data-invalid="!!errors.manufacturedOn" :data-disabled="disabled">
    <FieldLabel :for="`${idPrefix}-manufactured`">Дата производства</FieldLabel>
    <Input
      :id="`${idPrefix}-manufactured`"
      type="date"
      min="0001-01-01"
      max="9999-12-31"
      :model-value="values.manufacturedOn"
      :disabled="disabled"
      :aria-invalid="!!errors.manufacturedOn"
      :aria-describedby="`${idPrefix}-manufactured-error`"
      @change="commitDate('manufacturedOn', $event)"
      @update:model-value="change('manufacturedOn', $event)"
    />
    <FieldError
      :id="`${idPrefix}-manufactured-error`"
      :errors="[errors.manufacturedOn]"
    />
  </Field>
  <Field
    :data-invalid="!!errors.expiresOn"
    :data-disabled="disabled || expirationMode === 'NONE'"
  >
    <FieldLabel :for="`${idPrefix}-expires`">Срок годности</FieldLabel>
    <Input
      :id="`${idPrefix}-expires`"
      type="date"
      min="0001-01-01"
      max="9999-12-31"
      :model-value="values.expiresOn"
      :disabled="disabled || expirationMode === 'NONE'"
      :aria-invalid="!!errors.expiresOn"
      :aria-describedby="`${idPrefix}-expires-hint ${idPrefix}-expires-error`"
      @change="commitDate('expiresOn', $event)"
      @update:model-value="change('expiresOn', $event)"
    />
    <FieldDescription :id="`${idPrefix}-expires-hint`">{{
      expirationMode === "NONE"
        ? "В настройках SKU срок годности отключён."
        : expirationMode === "REQUIRED"
          ? "Срок понадобится перед поступлением. Сейчас поле необязательно."
          : "Необязательная дата-заметка."
    }}</FieldDescription>
    <FieldError
      :id="`${idPrefix}-expires-error`"
      :errors="[errors.expiresOn]"
    />
    <Button
      v-if="expirationMode === 'NONE' && values.expiresOn"
      type="button"
      variant="link"
      :disabled="disabled"
      @click="change('expiresOn', '')"
      >Очистить срок</Button
    >
  </Field>
</template>
