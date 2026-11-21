<script setup lang="ts">
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { InventoryItemDetails } from "../../model/inventory-item-settings.types";
defineProps<{
  item?: InventoryItemDetails;
  loading: boolean;
  error: string;
  pending: boolean;
  canRetry: boolean;
}>();
const emit = defineEmits<{ retry: [] }>();
</script>
<template>
  <div class="flex shrink-0 flex-col gap-3">
    <Alert v-if="error" variant="destructive"
      ><AlertDescription class="flex flex-wrap items-center gap-2"
        ><span>{{ error }}</span
        ><Button
          v-if="canRetry"
          type="button"
          size="sm"
          variant="outline"
          :disabled="pending"
          @click="emit('retry')"
          >Повторить загрузку SKU и единиц</Button
        ></AlertDescription
      ></Alert
    >
    <Skeleton
      v-if="loading && !item && !error"
      class="h-10 w-full"
      aria-label="Загрузка сведений о SKU"
    />
    <p v-if="item" class="break-words text-sm text-muted-foreground">
      SKU: <span class="font-mono break-all">{{ item.sku }}</span> · Базовая
      единица: {{ item.baseUom }} · Шаг:
      <span class="font-mono break-all">{{ item.quantityStep }}</span>
    </p>
    <Button
      v-if="item && !error"
      type="button"
      variant="ghost"
      size="sm"
      class="self-start"
      :disabled="pending"
      @click="emit('retry')"
      >Обновить сведения о SKU</Button
    >
  </div>
</template>
