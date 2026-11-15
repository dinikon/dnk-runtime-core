<script setup lang="ts">
import { ref, watch } from "vue";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  internalMoveStatuses,
  internalMoveStatusLabels,
} from "../../model/internal-move-page-state";
import type { InternalMovesParams } from "../../model/internal-move.types";
const props = defineProps<{ params: InternalMovesParams; disabled: boolean }>();
const emit = defineEmits<{ change: [v: Partial<InternalMovesParams>] }>();
const search = ref(props.params.search),
  from = ref(""),
  to = ref("");
function localValue(raw?: string): string {
  if (!raw) return "";
  const d = new Date(raw);
  if (!Number.isFinite(d.getTime())) return "";
  const offset = d.getTimezoneOffset();
  return new Date(d.getTime() - offset * 60_000).toISOString().slice(0, 16);
}
watch(
  () => props.params,
  (p) => {
    search.value = p.search;
    from.value = localValue(p.createdFrom);
    to.value = localValue(p.createdTo);
  },
  { immediate: true },
);
const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
function apply(): void {
  emit("change", {
    search: search.value,
    createdFrom: from.value ? new Date(from.value).toISOString() : undefined,
    createdTo: to.value ? new Date(to.value).toISOString() : undefined,
  });
}
</script>
<template>
  <form class="flex flex-col gap-3" @submit.prevent="apply">
    <div class="flex flex-wrap items-end gap-3">
      <label class="min-w-44 flex-1 text-sm"
        >Поиск по SKU<Input
          v-model="search"
          type="search"
          :disabled="disabled"
          placeholder="Исторический код товара" /></label
      ><label class="text-sm"
        >Статус<select
          aria-label="Статус перемещения"
          class="ml-2 h-9 rounded-md border bg-background px-2"
          :value="params.status"
          :disabled="disabled"
          @change="
            emit('change', {
              status: ($event.target as HTMLSelectElement)
                .value as InternalMovesParams['status'],
            })
          "
        >
          <option value="ALL">Все</option>
          <option
            v-for="status in internalMoveStatuses"
            :key="status"
            :value="status"
          >
            {{ internalMoveStatusLabels[status] }}
          </option>
        </select></label
      ><Button type="submit" variant="outline" :disabled="disabled"
        >Найти</Button
      >
    </div>
    <div class="flex flex-wrap items-end gap-3">
      <label class="text-sm"
        >Создано с<Input
          v-model="from"
          type="datetime-local"
          :disabled="disabled" /></label
      ><label class="text-sm"
        >Создано по<Input
          v-model="to"
          type="datetime-local"
          :disabled="disabled"
      /></label>
      <p class="text-xs text-muted-foreground">Время устройства: {{ zone }}.</p>
    </div>
  </form>
</template>
