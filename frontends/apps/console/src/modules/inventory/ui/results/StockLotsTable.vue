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
import type { StockLot } from "../../model/stock-lot.types";
import { displayStockDate } from "../../model/stock-lot.validation";
defineProps<{ items: readonly StockLot[]; disabled: boolean }>();
const emit = defineEmits<{ open: [id: string] }>();
</script>
<template>
  <div class="min-w-0 overflow-auto rounded-md border">
    <Table aria-label="Партии SKU"
      ><TableHeader
        ><TableRow
          ><TableHead>Номер партии</TableHead
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
