<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
  FieldError,
  FieldSet,
  FieldLegend,
} from "@/components/ui/field";
import type {
  InventoryItemEditValues,
  InventoryItemEditErrors,
} from "../../model/inventory-item-editor.types";
import type {
  InventoryItemSettings,
  InventoryUom,
} from "../../model/inventory-item-settings.types";
import InventoryItemSettingsFields from "./InventoryItemSettingsFields.vue";
import InventoryItemBarcodesFields from "./InventoryItemBarcodesFields.vue";
const props = defineProps<{
  values: InventoryItemEditValues;
  errors: InventoryItemEditErrors;
  uoms: readonly InventoryUom[];
  disabled: boolean;
  settingsDisabled: boolean;
  dirty: boolean;
  pending: boolean;
  canSubmit: boolean;
  uncertain: boolean;
}>();
const emit = defineEmits<{
  change: [value: InventoryItemEditValues];
  addBarcode: [];
  submit: [];
  reset: [];
}>();
function changeSettings(value: InventoryItemSettings): void {
  emit("change", { ...props.values, ...value });
}
</script>
<template>
  <form
    class="flex flex-col gap-7"
    aria-label="Карточка складской позиции"
    novalidate
    @submit.prevent="emit('submit')"
  >
    <FieldGroup>
      <Field :data-invalid="!!errors.fields.sku" :data-disabled="disabled">
        <FieldLabel for="inventory-edit-sku">Код SKU</FieldLabel>
        <Input
          id="inventory-edit-sku"
          :model-value="values.sku"
          type="text"
          autocomplete="off"
          :spellcheck="false"
          class="font-mono"
          :disabled="disabled"
          :aria-invalid="!!errors.fields.sku"
          aria-describedby="inventory-edit-sku-hint inventory-edit-sku-error"
          @update:model-value="
            emit('change', { ...values, sku: String($event) })
          "
        />
        <FieldDescription id="inventory-edit-sku-hint"
          >Ручной код до 25 символов после нормализации. Регистр SKU не
          различается; сохранённый код покажет сервер.</FieldDescription
        >
        <FieldError
          id="inventory-edit-sku-error"
          :errors="[errors.fields.sku]"
        />
      </Field>
    </FieldGroup>
    <InventoryItemBarcodesFields
      :values="values.barcodes"
      :errors="errors.barcodeRows"
      :error="errors.fields.barcodes"
      :disabled="disabled"
      @change="emit('change', { ...values, barcodes: $event })"
      @add="emit('addBarcode')"
    />
    <FieldSet>
      <FieldLegend>Параметры складского учёта</FieldLegend>
      <InventoryItemSettingsFields
        :values="values"
        :errors="errors.fields"
        :uoms="uoms"
        :disabled="disabled || settingsDisabled"
        @change="changeSettings"
      />
    </FieldSet>
    <div class="flex flex-wrap items-center gap-3">
      <Button
        type="submit"
        :disabled="disabled || pending || !dirty || !canSubmit"
        >{{ pending ? "Сохранение…" : "Сохранить" }}</Button
      >
      <Button
        type="button"
        variant="outline"
        :disabled="disabled || pending || !dirty || uncertain"
        @click="emit('reset')"
        >Сбросить изменения</Button
      >
    </div>
  </form>
</template>
