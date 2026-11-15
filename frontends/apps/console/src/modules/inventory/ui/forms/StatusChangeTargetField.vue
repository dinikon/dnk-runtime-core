<script setup lang="ts">
import { computed, useId } from "vue";
import { stockStatusLabel } from "../../model/stock-accounting.constants";
import type { StatusTransition } from "../../model/status-change-preview.types";
import { Button } from "@/components/ui/button";
const props = defineProps<{
  value: string;
  transitions: StatusTransition[];
  sourceStatus?: string;
  disabled: boolean;
  loading: boolean;
  error?: string;
  fieldError?: string;
}>();
const emit = defineEmits<{ change: [value: string]; retry: [] }>();
const fieldId = useId();
const targets = computed(() =>
  props.sourceStatus
    ? (props.transitions.find((v) => v.sourceStatus === props.sourceStatus)
        ?.targetStatuses ?? [])
    : [...new Set(props.transitions.flatMap((v) => v.targetStatuses))],
);
</script>
<template>
  <div class="space-y-2">
    <label :for="fieldId" class="text-sm font-medium">Новое состояние</label>
    <select
      :id="fieldId"
      class="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm"
      :value="value"
      :disabled="disabled || loading || !!error"
      @change="emit('change', ($event.target as HTMLSelectElement).value)"
    >
      <option value="" disabled>Выберите состояние</option>
      <option v-for="target in targets" :key="target" :value="target">
        {{ stockStatusLabel(target) }}
      </option>
    </select>
    <p v-if="loading" role="status" class="text-sm">Загрузка переходов…</p>
    <p v-if="error" role="alert" class="text-sm text-destructive">
      {{ error }}
      <Button type="button" variant="outline" @click="emit('retry')"
        >Повторить загрузку переходов</Button
      >
    </p>
    <p v-if="fieldError" role="alert" class="text-sm text-destructive">
      {{ fieldError }}
    </p>
    <p class="text-xs text-muted-foreground">
      Меняется только состояние. Локация, владелец, партия и серия сохраняются.
    </p>
  </div>
</template>
