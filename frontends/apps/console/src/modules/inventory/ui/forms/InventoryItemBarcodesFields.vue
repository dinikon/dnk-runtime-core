<script setup lang="ts">
import { nextTick } from "vue";
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
import type { InventoryBarcodeInput } from "../../model/inventory-item-editor.types";
const props = defineProps<{
  values: readonly InventoryBarcodeInput[];
  errors: Record<string, string>;
  error?: string;
  disabled: boolean;
}>();
const emit = defineEmits<{
  change: [values: InventoryBarcodeInput[]];
  add: [];
}>();
function change(key: string, barcode: string): void {
  emit(
    "change",
    props.values.map((row) =>
      row.key === key ? { ...row, barcode } : { ...row },
    ),
  );
}
async function add(): Promise<void> {
  emit("add");
  await nextTick();
  const row = props.values.at(-1);
  if (row) document.getElementById(`inventory-barcode-${row.key}`)?.focus();
}
async function remove(key: string): Promise<void> {
  emit(
    "change",
    props.values.filter((row) => row.key !== key),
  );
  await nextTick();
  document.getElementById("inventory-barcode-add")?.focus();
}
</script>
<template>
  <FieldSet>
    <FieldLegend>Штрихкоды</FieldLegend>
    <FieldDescription
      >Штрихкод идентифицирует SKU. Ведущие нули и регистр сохраняются; упаковка
      по нему не определяется.</FieldDescription
    >
    <FieldGroup>
      <Field
        v-for="(row, index) in values"
        :key="row.key"
        :data-invalid="!!errors[row.key]"
        :data-disabled="disabled"
      >
        <FieldLabel :for="`inventory-barcode-${row.key}`"
          >Штрихкод {{ index + 1 }}</FieldLabel
        >
        <div class="flex min-w-0 flex-wrap items-start gap-2">
          <Input
            :id="`inventory-barcode-${row.key}`"
            :model-value="row.barcode"
            type="text"
            autocomplete="off"
            :spellcheck="false"
            class="min-w-0 flex-1 basis-48 font-mono"
            :disabled="disabled"
            :aria-invalid="!!errors[row.key]"
            :aria-describedby="`inventory-barcode-error-${row.key}`"
            @update:model-value="change(row.key, String($event))"
          />
          <Button
            type="button"
            variant="outline"
            :disabled="disabled"
            :aria-label="`Удалить штрихкод ${index + 1}`"
            @click="remove(row.key)"
            >Удалить</Button
          >
        </div>
        <FieldError
          :id="`inventory-barcode-error-${row.key}`"
          :errors="[errors[row.key]]"
        />
      </Field>
      <FieldDescription v-if="!values.length"
        >Штрихкодов пока нет.</FieldDescription
      >
      <FieldError :errors="[error]" />
    </FieldGroup>
    <Button
      id="inventory-barcode-add"
      type="button"
      variant="outline"
      class="self-start"
      :disabled="disabled"
      @click="add"
      >Добавить штрихкод</Button
    >
  </FieldSet>
</template>
