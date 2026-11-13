<script setup lang="ts">
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  STOCK_LOCATION_TYPES,
  STOCK_LOCATION_TYPE_LABELS,
  isStockLocationType,
} from "../../model/stock-location.constants";
import type { StockLocationType } from "../../model/stock-location.types";
const props = defineProps<{
  id: string;
  value: StockLocationType | null;
  label: string;
  allowAll?: boolean;
  disabled?: boolean;
  invalid?: boolean;
}>();
const emit = defineEmits<{ change: [value: StockLocationType | null] }>();
function choose(value: unknown): void {
  if (isStockLocationType(value)) emit("change", value);
  else if (props.allowAll && value === "all") emit("change", null);
}
</script>
<template>
  <Select
    :model-value="value ?? (allowAll ? 'all' : undefined)"
    :disabled="disabled"
    @update:model-value="choose"
  >
    <SelectTrigger
      :id="id"
      class="w-full"
      :aria-label="label"
      :aria-invalid="invalid"
      ><SelectValue placeholder="Выберите тип"
    /></SelectTrigger>
    <SelectContent
      ><SelectGroup
        ><SelectItem v-if="allowAll" value="all">Все типы</SelectItem
        ><SelectItem
          v-for="type in STOCK_LOCATION_TYPES"
          :key="type"
          :value="type"
          >{{ STOCK_LOCATION_TYPE_LABELS[type] }}</SelectItem
        ></SelectGroup
      ></SelectContent
    >
  </Select>
</template>
