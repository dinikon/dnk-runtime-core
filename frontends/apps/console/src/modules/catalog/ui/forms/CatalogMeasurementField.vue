<script setup lang="ts" generic="U extends WeightUnit | LengthUnit">
import { ref, watch, useId } from "vue";
import type {
  ProductMeasurement,
  WeightUnit,
  LengthUnit,
} from "../../model/product.types";
import { convertMeasurement } from "../../model/measurement-conversion";
import {
  Field,
  FieldLabel,
  FieldDescription,
  FieldError,
} from "@/components/ui/field";
import {
  InputGroup,
  InputGroupInput,
  InputGroupAddon,
} from "@/components/ui/input-group";
const fieldId = useId();
const props = defineProps<{
  label: string;
  modelValue: ProductMeasurement<U> | null;
  effective: ProductMeasurement<U> | null;
  units: readonly U[];
  defaultUnit: U;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: ProductMeasurement<U> | null];
}>();
const value = ref("");
const unit = ref<U>(props.defaultUnit);
const error = ref("");
const labels = { g: "г", kg: "кг", cm: "см", m: "м" };
watch(
  () => props.modelValue,
  (next) => {
    value.value = next?.value ?? "";
    unit.value = next?.unit ?? unit.value;
  },
  { immediate: true },
);
function input(next: string | number) {
  value.value = String(next);
  error.value = "";
  emit(
    "update:modelValue",
    value.value.trim() ? { value: value.value, unit: unit.value } : null,
  );
}
function changeUnit(event: Event) {
  const select = event.target as HTMLSelectElement;
  const next = select.value as U;
  if (value.value.trim()) {
    const converted = convertMeasurement(value.value, unit.value, next);
    if (converted === null) {
      error.value = "Введите корректное число перед сменой единицы.";
      select.value = unit.value;
      return;
    }
    value.value = converted;
  }
  unit.value = next;
  if (value.value.trim())
    emit("update:modelValue", { value: value.value, unit: next });
}
</script>

<template>
  <Field class="min-w-0" :data-invalid="!!error || undefined">
    <FieldLabel :for="fieldId">{{ label }}</FieldLabel>
    <InputGroup>
      <InputGroupInput
        :id="fieldId"
        :model-value="value"
        :aria-label="label"
        :aria-invalid="!!error || undefined"
        :aria-describedby="`${fieldId}-hint`"
        inputmode="decimal"
        placeholder="Не задано"
        @update:model-value="input"
      />
      <InputGroupAddon align="inline-end"
        ><select
          :value="unit"
          :aria-label="`Единица: ${label}`"
          class="rounded bg-transparent p-1 text-sm text-foreground"
          @change="changeUnit"
        >
          <option v-for="option in units" :key="option" :value="option">
            {{ labels[option] }}
          </option>
        </select></InputGroupAddon
      >
    </InputGroup>
    <FieldError v-if="error">{{ error }}</FieldError>
    <FieldDescription :id="`${fieldId}-hint`"
      >Текущее значение:
      {{
        effective ? `${effective.value} ${labels[effective.unit]}` : "Не задано"
      }}</FieldDescription
    >
  </Field>
</template>
