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
  WarehouseEditValues,
  WarehouseFieldErrors,
} from "../../model/warehouse.types";
const props = defineProps<{
  values: WarehouseEditValues;
  errors: WarehouseFieldErrors;
  pending: boolean;
  disabled: boolean;
  dirty: boolean;
  saveBlocked?: boolean;
}>();
const emit = defineEmits<{
  change: [values: WarehouseEditValues];
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
        <FieldLabel for="warehouse-code">Код склада</FieldLabel
        ><Input
          id="warehouse-code"
          :model-value="values.code"
          :disabled="disabled"
          :aria-invalid="!!errors.code"
          aria-describedby="warehouse-code-error"
          autocomplete="off"
          autocapitalize="none"
          spellcheck="false"
          @update:model-value="change('code', $event)"
        /><FieldError id="warehouse-code-error" :errors="[errors.code]" />
      </Field>
      <Field :data-invalid="!!errors.name" :data-disabled="disabled">
        <FieldLabel for="warehouse-name">Название склада</FieldLabel
        ><Input
          id="warehouse-name"
          :model-value="values.name"
          :disabled="disabled"
          :aria-invalid="!!errors.name"
          aria-describedby="warehouse-name-error"
          autocomplete="off"
          @update:model-value="change('name', $event)"
        /><FieldError id="warehouse-name-error" :errors="[errors.name]" />
      </Field>
      <Field
        orientation="horizontal"
        :data-invalid="!!errors.isActive"
        :data-disabled="disabled"
      >
        <FieldContent
          ><FieldLabel for="warehouse-active">Склад активен</FieldLabel
          ><FieldDescription id="warehouse-active-hint"
            >Деактивация административно блокирует склад. Локации и их
            собственная активность сохраняются.</FieldDescription
          ><FieldError id="warehouse-active-error" :errors="[errors.isActive]"
        /></FieldContent>
        <Switch
          id="warehouse-active"
          :model-value="values.isActive"
          :disabled="disabled"
          :aria-invalid="!!errors.isActive"
          aria-describedby="warehouse-active-hint warehouse-active-error"
          @update:model-value="emit('change', { ...values, isActive: $event })"
        />
      </Field>
    </FieldGroup>
    <div class="flex flex-wrap gap-2">
      <Button
        type="submit"
        :disabled="disabled || pending || saveBlocked || !dirty"
        >{{ pending ? "Сохранение…" : "Сохранить" }}</Button
      ><Button
        type="button"
        variant="outline"
        :disabled="disabled || pending || saveBlocked || !dirty"
        @click="emit('reset')"
        >Сбросить изменения</Button
      >
    </div>
  </form>
</template>
