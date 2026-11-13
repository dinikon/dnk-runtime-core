<script setup lang="ts">
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
  FieldError,
  FieldContent,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import type {
  StockLocationEditValues,
  StockLocationFieldErrors,
} from "../../model/stock-location.types";
const props = defineProps<{
  values: StockLocationEditValues;
  errors: StockLocationFieldErrors;
  pending: boolean;
  disabled: boolean;
  dirty: boolean;
  saveDisabled: boolean;
  isDefault: boolean | null;
}>();
const emit = defineEmits<{
  change: [values: StockLocationEditValues];
  submit: [];
  reset: [];
}>();
function change(field: "code" | "name", value: string | number): void {
  emit("change", { ...props.values, [field]: String(value) });
}
</script>
<template>
  <form
    class="flex flex-col gap-6"
    novalidate
    :aria-busy="pending"
    @submit.prevent="emit('submit')"
  >
    <FieldGroup>
      <Field :data-invalid="!!errors.code" :data-disabled="disabled">
        <FieldLabel for="stock-location-code">Код локации</FieldLabel
        ><Input
          id="stock-location-code"
          :model-value="values.code"
          :disabled="disabled"
          :aria-invalid="!!errors.code"
          aria-describedby="stock-location-code-error"
          autocomplete="off"
          autocapitalize="none"
          spellcheck="false"
          @update:model-value="change('code', $event)"
        /><FieldError id="stock-location-code-error" :errors="[errors.code]" />
      </Field>
      <Field :data-invalid="!!errors.name" :data-disabled="disabled">
        <FieldLabel for="stock-location-name">Название локации</FieldLabel
        ><Input
          id="stock-location-name"
          :model-value="values.name"
          :disabled="disabled"
          :aria-invalid="!!errors.name"
          aria-describedby="stock-location-name-error"
          autocomplete="off"
          @update:model-value="change('name', $event)"
        /><FieldError id="stock-location-name-error" :errors="[errors.name]" />
      </Field>
      <Field
        orientation="horizontal"
        :data-invalid="!!errors.isActive"
        :data-disabled="disabled"
      >
        <FieldContent
          ><FieldLabel for="stock-location-active">Локация активна</FieldLabel
          ><FieldDescription id="stock-location-active-hint">{{
            isDefault === true
              ? "Основную STORAGE нельзя деактивировать. Сначала требуется её переназначение."
              : isDefault === null
                ? "Для изменения активности загрузите сведения о складе."
                : "Активность локальная: родитель, дочерние локации и склад не изменяются."
          }}</FieldDescription
          ><FieldError
            id="stock-location-active-error"
            :errors="[errors.isActive]"
        /></FieldContent>
        <Switch
          id="stock-location-active"
          :model-value="values.isActive"
          :disabled="
            disabled || isDefault === null || (isDefault && values.isActive)
          "
          :aria-invalid="!!errors.isActive"
          aria-describedby="stock-location-active-hint stock-location-active-error"
          @update:model-value="emit('change', { ...values, isActive: $event })"
        />
      </Field>
    </FieldGroup>
    <div class="flex flex-wrap gap-2">
      <Button
        type="submit"
        :disabled="disabled || saveDisabled || pending || !dirty"
        >{{ pending ? "Сохранение…" : "Сохранить" }}</Button
      ><Button
        type="button"
        variant="outline"
        :disabled="disabled || pending || !dirty"
        @click="emit('reset')"
        >Сбросить изменения</Button
      >
    </div>
  </form>
</template>
