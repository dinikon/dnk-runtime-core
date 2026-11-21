<script setup lang="ts">
import { Button } from "@/components/ui/button";
import type { StockSerial } from "../../model/stock-serial.types";
import { displayStockDate } from "../../model/stock-lot.validation";
defineProps<{ serial: StockSerial }>();
const emit = defineEmits<{ lot: [id: string] }>();
</script>
<template>
  <dl class="grid min-w-0 gap-4 rounded-md border p-5 sm:grid-cols-2">
    <div class="min-w-0 sm:col-span-2">
      <dt class="text-sm text-muted-foreground">Серийный номер</dt>
      <dd class="break-all font-mono">{{ serial.number }}</dd>
    </div>
    <div class="min-w-0 sm:col-span-2">
      <dt class="text-sm text-muted-foreground">Источник дат</dt>
      <dd v-if="serial.dateSource === 'LOT'">
        Даты связанной партии
        <Button
          v-if="serial.lotId"
          variant="link"
          class="h-auto max-w-full whitespace-normal break-all px-0 font-mono"
          @click="emit('lot', serial.lotId)"
          >{{ serial.lotNumber }}</Button
        >
        <p class="text-sm text-muted-foreground">
          Даты изменяются в карточке партии.
        </p>
      </dd>
      <dd v-else>Нет партии — даты отсутствуют.</dd>
    </div>
    <template v-if="serial.dateSource === 'LOT'"
      ><div>
        <dt class="text-sm text-muted-foreground">Дата производства</dt>
        <dd>{{ displayStockDate(serial.manufacturedOn) }}</dd>
      </div>
      <div>
        <dt class="text-sm text-muted-foreground">Срок годности</dt>
        <dd>{{ displayStockDate(serial.expiresOn) }}</dd>
      </div></template
    >
  </dl>
</template>
