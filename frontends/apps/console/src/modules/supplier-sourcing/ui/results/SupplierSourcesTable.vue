<script setup lang="ts">
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { SupplierSource } from "../../model/supplier-source.types";
import { fulfillmentLabels } from "../../model/supplier-source.constants";
defineProps<{ items: readonly SupplierSource[] }>();
const emit = defineEmits<{ open: [id: string] }>();
import { supplierTypeLabels } from "../../model/supplier-source.constants";
</script>
<template>
  <div class="min-w-0 overflow-x-auto rounded-md border">
    <Table
      ><TableHeader
        ><TableRow
          ><TableHead>Источник</TableHead><TableHead>Поставщик</TableHead
          ><TableHead>Внешний код</TableHead><TableHead>Исполнение</TableHead
          ><TableHead>Срок / TTL</TableHead
          ><TableHead>Активность</TableHead></TableRow
        ></TableHeader
      ><TableBody
        ><TableRow v-for="source in items" :key="source.id"
          ><TableCell
            ><Button
              variant="link"
              class="h-auto whitespace-normal p-0 text-left"
              @click="emit('open', source.id)"
              >{{ source.name }}</Button
            ></TableCell
          ><TableCell
            >{{ source.supplierName ?? source.supplierId }}
            <div class="text-xs text-muted-foreground">
              {{ supplierTypeLabels[source.supplierModelKey] }}
            </div></TableCell
          ><TableCell class="font-mono">{{
            source.externalWarehouseCode ?? "—"
          }}</TableCell
          ><TableCell
            ><div v-for="mode in source.fulfillmentModes" :key="mode">
              {{ fulfillmentLabels[mode] }}
            </div></TableCell
          ><TableCell class="tabular-nums"
            ><div>{{ source.defaultLeadTimeSeconds }} с</div>
            <div class="text-xs text-muted-foreground">
              TTL {{ source.stockUpdatePolicy.ttlSeconds }} с
            </div></TableCell
          ><TableCell
            ><Badge :variant="source.isActive ? 'secondary' : 'outline'">{{
              source.isActive ? "Активен" : "Неактивен"
            }}</Badge></TableCell
          ></TableRow
        ></TableBody
      ></Table
    >
  </div>
</template>
