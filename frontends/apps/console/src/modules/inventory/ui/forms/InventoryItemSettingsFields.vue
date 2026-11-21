<script setup lang="ts">
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldTitle,
  FieldDescription,
  FieldError,
} from "@/components/ui/field";
import {
  NativeSelect,
  NativeSelectOption,
  NativeSelectOptGroup,
} from "@/components/ui/native-select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  inventoryTrackingLabels,
  inventoryExpirationLabels,
} from "../../model/inventory-item.constants";
import type {
  InventoryItemSettings,
  InventorySettingsErrors,
  InventoryUom,
  InventoryUomDimension,
} from "../../model/inventory-item-settings.types";

const props = defineProps<{
  values: InventoryItemSettings;
  uoms: readonly InventoryUom[];
  errors: InventorySettingsErrors;
  disabled: boolean;
}>();
const emit = defineEmits<{
  change: [value: InventoryItemSettings];
}>();
const dimensions: Record<InventoryUomDimension, string> = {
  COUNT: "Количество",
  MASS: "Масса",
  VOLUME: "Объём",
  LENGTH: "Длина",
  AREA: "Площадь",
};
function change<K extends keyof InventoryItemSettings>(
  field: K,
  value: InventoryItemSettings[K],
): void {
  emit("change", { ...props.values, [field]: value });
}
</script>

<template>
  <FieldGroup>
    <Field :data-invalid="!!errors.baseUom" :data-disabled="disabled">
      <FieldLabel for="inventory-base-uom"
        >Базовая единица измерения</FieldLabel
      >
      <NativeSelect
        id="inventory-base-uom"
        :model-value="values.baseUom"
        :disabled="disabled"
        :aria-invalid="!!errors.baseUom"
        aria-describedby="inventory-uom-hint inventory-uom-error"
        @update:model-value="change('baseUom', String($event ?? ''))"
      >
        <NativeSelectOptGroup
          v-for="(label, dimension) in dimensions"
          :key="dimension"
          :label="label"
        >
          <NativeSelectOption
            v-for="unit in uoms.filter((unit) => unit.dimension === dimension)"
            :key="unit.code"
            :value="unit.code"
            >{{ unit.code }}</NativeSelectOption
          >
        </NativeSelectOptGroup>
      </NativeSelect>
      <FieldDescription id="inventory-uom-hint"
        >Количество хранится в этой единице. Для серийного учёта выберите
        PCS.</FieldDescription
      >
      <FieldError id="inventory-uom-error" :errors="[errors.baseUom]" />
    </Field>
    <Field :data-invalid="!!errors.quantityStep" :data-disabled="disabled">
      <FieldLabel for="inventory-quantity-step">Шаг количества</FieldLabel>
      <Input
        id="inventory-quantity-step"
        type="text"
        inputmode="decimal"
        autocomplete="off"
        class="max-w-sm font-mono"
        :model-value="values.quantityStep"
        :disabled="disabled"
        :aria-invalid="!!errors.quantityStep"
        aria-describedby="inventory-step-hint inventory-step-error"
        @update:model-value="change('quantityStep', String($event))"
      />
      <FieldDescription id="inventory-step-hint"
        >Положительное число, например 1 или 0.001. Для серийного учёта — ровно
        1.</FieldDescription
      >
      <FieldError id="inventory-step-error" :errors="[errors.quantityStep]" />
    </Field>
    <Field :data-invalid="!!errors.trackingMode" :data-disabled="disabled">
      <FieldTitle id="inventory-tracking-label">Прослеживаемость</FieldTitle>
      <ToggleGroup
        type="single"
        :model-value="values.trackingMode"
        variant="outline"
        :spacing="2"
        class="flex-wrap"
        :disabled="disabled"
        :aria-invalid="!!errors.trackingMode"
        aria-labelledby="inventory-tracking-label"
        aria-describedby="inventory-tracking-hint inventory-tracking-error"
        @update:model-value="
          $event &&
          change(
            'trackingMode',
            $event as InventoryItemSettings['trackingMode'],
          )
        "
      >
        <ToggleGroupItem
          v-for="(label, mode) in inventoryTrackingLabels"
          :key="mode"
          :value="mode"
          >{{ label }}</ToggleGroupItem
        >
      </ToggleGroup>
      <FieldDescription id="inventory-tracking-hint"
        >Партии и серии определяют, как различать складские
        единицы.</FieldDescription
      >
      <FieldError
        id="inventory-tracking-error"
        :errors="[errors.trackingMode]"
      />
    </Field>
    <Field :data-invalid="!!errors.expirationMode" :data-disabled="disabled">
      <FieldTitle id="inventory-expiration-label"
        >Учёт срока годности</FieldTitle
      >
      <ToggleGroup
        type="single"
        :model-value="values.expirationMode"
        variant="outline"
        :spacing="2"
        class="flex-wrap"
        :disabled="disabled"
        :aria-invalid="!!errors.expirationMode"
        aria-labelledby="inventory-expiration-label"
        aria-describedby="inventory-expiration-hint inventory-expiration-error"
        @update:model-value="
          $event &&
          change(
            'expirationMode',
            $event as InventoryItemSettings['expirationMode'],
          )
        "
      >
        <ToggleGroupItem
          v-for="(label, mode) in inventoryExpirationLabels"
          :key="mode"
          :value="mode"
          >{{ label }}</ToggleGroupItem
        >
      </ToggleGroup>
      <FieldDescription id="inventory-expiration-hint"
        >Необязательная заметка позволяет указать дату без обязательного
        контроля срока. Обязательный срок требует партий или
        серий.</FieldDescription
      >
      <FieldError
        id="inventory-expiration-error"
        :errors="[errors.expirationMode]"
      />
    </Field>
  </FieldGroup>
</template>
