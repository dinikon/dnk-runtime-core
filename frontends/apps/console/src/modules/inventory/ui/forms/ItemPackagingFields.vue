<script setup lang="ts">
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
  FieldError,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import type {
  ItemPackagingValues,
  ItemPackagingErrors,
  PackagingTypePickerState,
} from "../../model/item-packaging.types";
import type { InventoryUom } from "../../model/inventory-item-settings.types";
import ItemPackagingTypePicker from "./ItemPackagingTypePicker.vue";
const props = defineProps<{
  prefix: string;
  values: ItemPackagingValues;
  errors: ItemPackagingErrors;
  uoms: readonly InventoryUom[];
  picker: PackagingTypePickerState;
  disabled: boolean;
}>();
const emit = defineEmits<{
  change: [value: ItemPackagingValues];
  typeSearch: [value: string];
  typeOpen: [value: boolean];
  typeMore: [];
  typeRetry: [];
  typeRetrySelected: [];
}>();
function change(
  field: keyof ItemPackagingValues,
  value: string | number,
): void {
  emit("change", { ...props.values, [field]: String(value) });
}
</script>
<template>
  <FieldGroup>
    <Field :data-invalid="!!errors.packagingTypeId" :data-disabled="disabled">
      <FieldLabel :for="`${prefix}-type`">Тип тары</FieldLabel>
      <ItemPackagingTypePicker
        :id="`${prefix}-type`"
        label="Тип тары"
        empty-label="Очистить выбор"
        :search="picker.search"
        :options="picker.options"
        :total="picker.total"
        :loading="picker.loading"
        :fetching-more="picker.fetchingMore"
        :has-more="picker.hasMore"
        :error="picker.error"
        :selected-id="values.packagingTypeId"
        :selected="picker.selected"
        :selected-loading="picker.selectedLoading"
        :selected-error="picker.selectedError"
        :disabled="disabled"
        :invalid="!!errors.packagingTypeId"
        :describedby="`${prefix}-type-error`"
        @search="emit('typeSearch', $event)"
        @select="change('packagingTypeId', $event)"
        @open="emit('typeOpen', $event)"
        @more="emit('typeMore')"
        @retry="emit('typeRetry')"
        @retry-selected="emit('typeRetrySelected')"
      />
      <FieldError
        :id="`${prefix}-type-error`"
        :errors="[errors.packagingTypeId]"
      />
    </Field>
    <Field :data-invalid="!!errors.code" :data-disabled="disabled">
      <FieldLabel :for="`${prefix}-code`">Код упаковки</FieldLabel>
      <Input
        :id="`${prefix}-code`"
        :model-value="values.code"
        :disabled="disabled"
        :aria-invalid="!!errors.code"
        :aria-describedby="`${prefix}-code-hint ${prefix}-code-error`"
        autocomplete="off"
        autocapitalize="none"
        spellcheck="false"
        @update:model-value="change('code', $event)"
      />
      <FieldDescription :id="`${prefix}-code-hint`"
        >Регистр значим: BOX и box — разные коды внутри SKU.</FieldDescription
      >
      <FieldError :id="`${prefix}-code-error`" :errors="[errors.code]" />
    </Field>
    <Field :data-invalid="!!errors.name" :data-disabled="disabled">
      <FieldLabel :for="`${prefix}-name`">Название упаковки</FieldLabel>
      <Input
        :id="`${prefix}-name`"
        :model-value="values.name"
        :disabled="disabled"
        :aria-invalid="!!errors.name"
        :aria-describedby="`${prefix}-name-error`"
        autocomplete="off"
        @update:model-value="change('name', $event)"
      />
      <FieldError :id="`${prefix}-name-error`" :errors="[errors.name]" />
    </Field>
    <Field :data-invalid="!!errors.contentQuantity" :data-disabled="disabled">
      <FieldLabel :for="`${prefix}-quantity`"
        >Количество содержимого</FieldLabel
      >
      <Input
        :id="`${prefix}-quantity`"
        type="text"
        inputmode="decimal"
        :model-value="values.contentQuantity"
        :disabled="disabled"
        :aria-invalid="!!errors.contentQuantity"
        :aria-describedby="`${prefix}-quantity-hint ${prefix}-quantity-error`"
        autocomplete="off"
        @update:model-value="change('contentQuantity', $event)"
      />
      <FieldDescription :id="`${prefix}-quantity-hint`"
        >Положительное количество в указанной единице, например 12 или 0.5. Оно
        должно соответствовать шагу учёта SKU.</FieldDescription
      >
      <FieldError
        :id="`${prefix}-quantity-error`"
        :errors="[errors.contentQuantity]"
      />
    </Field>
    <Field :data-invalid="!!errors.contentUom" :data-disabled="disabled">
      <FieldLabel :for="`${prefix}-uom`">Единица содержимого</FieldLabel>
      <NativeSelect
        :id="`${prefix}-uom`"
        :model-value="values.contentUom"
        :disabled="disabled"
        :aria-invalid="!!errors.contentUom"
        :aria-describedby="`${prefix}-uom-hint ${prefix}-uom-error`"
        @update:model-value="change('contentUom', String($event ?? ''))"
      >
        <NativeSelectOption v-if="!values.contentUom" value="" disabled
          >Выберите единицу</NativeSelectOption
        >
        <NativeSelectOption
          v-if="
            values.contentUom &&
            !uoms.some((unit) => unit.code === values.contentUom)
          "
          :value="values.contentUom"
          disabled
          >{{ values.contentUom }} — несовместима с SKU</NativeSelectOption
        >
        <NativeSelectOption
          v-for="unit in uoms"
          :key="unit.code"
          :value="unit.code"
          >{{ unit.code }}</NativeSelectOption
        >
      </NativeSelect>
      <FieldDescription :id="`${prefix}-uom-hint`"
        >При смене только единицы числовое количество
        сохраняется.</FieldDescription
      >
      <FieldError :id="`${prefix}-uom-error`" :errors="[errors.contentUom]" />
    </Field>
  </FieldGroup>
</template>
