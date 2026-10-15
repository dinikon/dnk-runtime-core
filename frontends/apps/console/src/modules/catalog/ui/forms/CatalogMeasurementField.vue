<script setup lang="ts" generic="U extends WeightUnit | LengthUnit">
import { ref, watch } from "vue";
import type {
  MeasurementDTO,
  WeightUnit,
  LengthUnit,
} from "../../api/catalog.dto";
import { convertMeasurement } from "../../model/measurement-conversion";
const props = defineProps<{
  label: string;
  modelValue: MeasurementDTO<U> | null;
  effective: MeasurementDTO<U> | null;
  units: readonly U[];
  defaultUnit: U;
  inherited: boolean;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: MeasurementDTO<U> | null];
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
function input(event: Event) {
  value.value = (event.target as HTMLInputElement).value;
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
  <div class="space-y-1">
    <label class="block">
      <span>{{ label }}</span>
      <input
        :value="value"
        :aria-label="label"
        inputmode="decimal"
        placeholder="Не задано"
        class="w-full rounded border bg-background p-2"
        @input="input"
      />
    </label>
    <select
      :value="unit"
      :aria-label="`Единица: ${label}`"
      class="w-full rounded border bg-background p-2"
      @change="changeUnit"
    >
      <option v-for="option in units" :key="option" :value="option">
        {{ labels[option] }}
      </option>
    </select>
    <p v-if="error" class="text-sm text-destructive">{{ error }}</p>
    <p class="text-sm text-muted-foreground">
      {{ inherited ? "От родителя" : "Эффективно" }}:
      {{
        effective ? `${effective.value} ${labels[effective.unit]}` : "Не задано"
      }}
    </p>
  </div>
</template>
