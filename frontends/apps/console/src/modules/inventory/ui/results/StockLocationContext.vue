<script setup lang="ts">
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { Warehouse } from "../../model/warehouse.types";
import type { StockLocation } from "../../model/stock-location.types";
import { STOCK_LOCATION_TYPE_LABELS } from "../../model/stock-location.constants";
defineProps<{
  item: StockLocation;
  warehouse?: Warehouse;
  parent?: StockLocation;
  parentLoading: boolean;
  parentError: string;
  isDefault: boolean | null;
}>();
const emit = defineEmits<{ retryParent: [] }>();
</script>
<template>
  <dl class="grid gap-4 text-sm sm:grid-cols-3">
    <div class="min-w-0">
      <dt class="text-muted-foreground">Склад</dt>
      <dd class="break-words">
        {{
          warehouse
            ? `${warehouse.code} — ${warehouse.name}`
            : "Сведения о складе недоступны"
        }}
      </dd>
    </div>
    <div>
      <dt class="text-muted-foreground">Тип</dt>
      <dd>{{ STOCK_LOCATION_TYPE_LABELS[item.locationType] }}</dd>
    </div>
    <div class="min-w-0">
      <dt class="text-muted-foreground">Родитель</dt>
      <dd v-if="!item.parentLocationId">Корневая локация</dd>
      <dd v-else-if="parent" class="break-words">
        {{ parent.code }} — {{ parent.name }}
      </dd>
      <dd v-else>
        {{ parentLoading ? "Загрузка родителя…" : "Родитель недоступен" }}
      </dd>
    </div>
  </dl>
  <Badge v-if="isDefault" variant="secondary">Основная STORAGE</Badge>
  <Alert v-if="parentError" variant="destructive"
    ><AlertDescription class="flex flex-wrap items-center gap-2"
      ><span>{{ parentError }}</span
      ><Button
        type="button"
        size="sm"
        variant="outline"
        :disabled="parentLoading"
        @click="emit('retryParent')"
        >Повторить загрузку родителя</Button
      ></AlertDescription
    ></Alert
  >
</template>
