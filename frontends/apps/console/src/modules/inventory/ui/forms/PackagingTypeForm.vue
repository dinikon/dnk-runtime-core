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
  PackagingTypeEditValues,
  PackagingTypeFieldErrors,
} from "../../model/packaging-type.types";
const props = defineProps<{
  values: PackagingTypeEditValues;
  errors: PackagingTypeFieldErrors;
  pending: boolean;
  disabled: boolean;
  dirty: boolean;
}>();
const emit = defineEmits<{
  change: [values: PackagingTypeEditValues];
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
        <FieldLabel for="packaging-type-code">Код типа тары</FieldLabel
        ><Input
          id="packaging-type-code"
          :model-value="values.code"
          :disabled="disabled"
          :aria-invalid="!!errors.code"
          aria-describedby="packaging-type-code-hint packaging-type-code-error"
          autocomplete="off"
          autocapitalize="none"
          spellcheck="false"
          @update:model-value="change('code', $event)"
        />
        <FieldDescription id="packaging-type-code-hint"
          >Регистр значим: BOX и box — разные коды.</FieldDescription
        >
        <FieldError id="packaging-type-code-error" :errors="[errors.code]" />
      </Field>
      <Field :data-invalid="!!errors.name" :data-disabled="disabled">
        <FieldLabel for="packaging-type-name">Название типа тары</FieldLabel
        ><Input
          id="packaging-type-name"
          :model-value="values.name"
          :disabled="disabled"
          :aria-invalid="!!errors.name"
          aria-describedby="packaging-type-name-error"
          autocomplete="off"
          @update:model-value="change('name', $event)"
        /><FieldError id="packaging-type-name-error" :errors="[errors.name]" />
      </Field>
      <Field
        orientation="horizontal"
        :data-invalid="!!errors.isActive"
        :data-disabled="disabled"
      >
        <FieldContent
          ><FieldLabel for="packaging-type-active">Тип тары активен</FieldLabel
          ><FieldDescription id="packaging-type-active-hint"
            >Деактивация запрещает новые назначения типа тары. Существующие
            варианты упаковки сохраняются.</FieldDescription
          ><FieldError
            id="packaging-type-active-error"
            :errors="[errors.isActive]"
        /></FieldContent>
        <Switch
          id="packaging-type-active"
          :model-value="values.isActive"
          :disabled="disabled"
          :aria-invalid="!!errors.isActive"
          aria-describedby="packaging-type-active-hint packaging-type-active-error"
          @update:model-value="emit('change', { ...values, isActive: $event })"
        />
      </Field>
    </FieldGroup>
    <div class="flex flex-wrap gap-2">
      <Button type="submit" :disabled="disabled || pending || !dirty">{{
        pending ? "Сохранение…" : "Сохранить"
      }}</Button
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
