<script setup lang="ts">
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import StockLotCard from "./StockLotCard.vue";
import type { StockLot } from "../../model/stock-lot.types";
defineProps<{
  lot?: StockLot;
  loading: boolean;
  refreshing: boolean;
  error: string;
}>();
const emit = defineEmits<{ retry: [] }>();
</script>
<template>
  <div class="flex flex-col gap-4" :aria-busy="loading || refreshing">
    <Alert v-if="error" variant="destructive"
      ><AlertDescription class="flex flex-wrap items-center gap-3"
        ><span>{{ error }}</span
        ><Button variant="outline" :disabled="refreshing" @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <slot v-if="lot" :lot="lot"><StockLotCard :lot="lot" /></slot
    ><Skeleton
      v-else-if="loading"
      class="h-48 w-full"
      aria-label="Загрузка партии"
    />
  </div>
</template>
