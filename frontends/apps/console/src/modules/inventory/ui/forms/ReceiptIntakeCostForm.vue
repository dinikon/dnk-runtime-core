<script setup lang="ts">
import { Input } from "@/components/ui/input";
import type { IntakeUnallocatedCost } from "../../model/receipt-posting.types";
const props = defineProps<{
  value: IntakeUnallocatedCost;
  disabled: boolean;
  error: string;
}>();
const emit = defineEmits<{ change: [value: IntakeUnallocatedCost] }>();
function change(fields: Partial<IntakeUnallocatedCost>): void {
  emit("change", { ...props.value, ...fields });
}
</script>
<template>
  <details class="rounded-md border p-3">
    <summary class="cursor-pointer text-sm">
      Сумма текущей приёмки без распределения
    </summary>
    <label class="mt-3 flex items-center gap-2 text-sm"
      ><input
        type="checkbox"
        :checked="value.known"
        :disabled="disabled"
        @change="change({ known: ($event.target as HTMLInputElement).checked })"
      />Сумма этой приёмки известна, распределение по строкам пока
      неизвестно</label
    >
    <div v-if="value.known" class="mt-3 grid gap-3 sm:grid-cols-2">
      <label class="text-sm"
        >Нераспределённая сумма<Input
          :model-value="value.amount"
          type="text"
          inputmode="decimal"
          :disabled="disabled"
          @update:model-value="change({ amount: String($event) })"
      /></label>
      <label class="text-sm"
        >Валюта общей суммы<Input
          :model-value="value.currency"
          maxlength="3"
          :disabled="disabled"
          @update:model-value="change({ currency: String($event) })"
      /></label>
      <label class="text-sm sm:col-span-2"
        >Основание общей суммы<Input
          :model-value="value.reference"
          maxlength="200"
          :disabled="disabled"
          @update:model-value="change({ reference: String($event) })"
      /></label>
    </div>
    <p class="mt-2 text-xs text-muted-foreground">
      Сумма относится только к этой приёмке. Стоимость следующих приёмок
      указывается отдельно.
    </p>
    <p v-if="error" role="alert" class="mt-2 text-sm text-destructive">
      {{ error }}
    </p>
  </details>
</template>
