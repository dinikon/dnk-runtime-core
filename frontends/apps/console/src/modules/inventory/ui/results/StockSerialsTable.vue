<script setup lang="ts">
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { StockSerial } from "../../model/stock-serial.types";
import { displayStockDate } from "../../model/stock-lot.validation";
defineProps<{ items: readonly StockSerial[]; disabled: boolean }>();
const emit = defineEmits<{ open: [id: string] }>();
</script>
<template>
  <div class="min-w-0 overflow-auto rounded-md border">
    <Table
      ><caption class="sr-only">
        Серийные экземпляры SKU
      </caption>
      <TableHeader
        ><TableRow
          ><TableHead>Серийный номер</TableHead
          ><TableHead>Источник дат</TableHead><TableHead>Партия</TableHead
          ><TableHead>Дата производства</TableHead
          ><TableHead>Срок годности</TableHead></TableRow
        ></TableHeader
      >
      <TableBody
        ><TableRow v-for="lot in items" :key="lot.id"
          ><TableCell class="max-w-80"
            ><Button
              variant="link"
              class="h-auto max-w-full whitespace-normal break-all px-0 text-left font-mono"
              :disabled="disabled"
              @click="emit('open', lot.id)"
              >{{ lot.number }}</Button
            ></TableCell
          ><TableCell>{{
            lot.dateSource === "LOT" ? "Партия" : "Нет партии"
          }}</TableCell
          ><TableCell class="max-w-60 break-all font-mono">{{
            lot.lotNumber ?? "—"
          }}</TableCell
          ><TableCell class="whitespace-nowrap">{{
            displayStockDate(lot.manufacturedOn)
          }}</TableCell
          ><TableCell class="whitespace-nowrap">{{
            displayStockDate(lot.expiresOn)
          }}</TableCell></TableRow
        ></TableBody
      >
    </Table>
  </div>
</template>
