<script setup lang="ts">
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import StockSerialCard from "./StockSerialCard.vue";
import type { StockSerial } from "../../model/stock-serial.types";
defineProps<{
  serial?: StockSerial;
  loading: boolean;
  refreshing: boolean;
  error: string;
}>();
const emit = defineEmits<{ retry: []; lot: [id: string] }>();
</script>
<template>
  <div class="flex min-w-0 flex-col gap-4" :aria-busy="loading || refreshing">
    <Alert v-if="error" variant="destructive"
      ><AlertDescription
        >{{ error }}
        <Button variant="outline" :disabled="refreshing" @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <p v-if="refreshing" role="status" class="text-sm text-muted-foreground">
      Обновление экземпляра…
    </p>
    <slot v-if="serial" :serial="serial"
      ><StockSerialCard :serial="serial" @lot="emit('lot', $event)" /></slot
    ><Skeleton
      v-else-if="loading"
      class="h-48 w-full"
      aria-label="Загрузка экземпляра"
    />
  </div>
</template>
