<script setup lang="ts">
import {
  stockDocumentStatusLabel,
  stockOperationLabel,
} from "../../model/stock-accounting.constants";
import { Button } from "@/components/ui/button";
import type {
  ListStockExecutionsItem,
  ListStockPostingsItem,
} from "../../model/stock-accounting.types";
import type { StockAccountingTarget } from "../../model/stock-accounting-navigation";
defineProps<{
  items: readonly (ListStockExecutionsItem | ListStockPostingsItem)[];
  kind: "executions" | "postings";
}>();
const emit = defineEmits<{ navigate: [target: StockAccountingTarget] }>();
</script>
<template>
  <div class="min-w-0 overflow-x-auto rounded-md border">
    <table class="w-full text-left text-sm">
      <thead>
        <tr>
          <th class="p-3">Время</th>
          <th class="p-3">Операция / склад</th>
          <th class="p-3">Владелец</th>
          <th class="p-3">Документ</th>
          <th class="p-3">Факт</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id" class="border-t">
          <td class="whitespace-nowrap p-3">
            {{
              new Date(
                "executedAt" in item ? item.executedAt : item.postedAt,
              ).toLocaleString()
            }}
          </td>
          <td class="p-3">
            {{ stockOperationLabel(item.operationType) }} /
            {{ item.warehouseCode }}
          </td>
          <td class="p-3">{{ item.ownerName ?? item.ownerId }}</td>
          <td class="p-3">
            <Button
              variant="link"
              @click="
                emit('navigate', {
                  kind: 'document',
                  id: item.documentId,
                  operationType: item.operationType,
                })
              "
              >Документ</Button
            ><span class="block text-xs">{{
              stockDocumentStatusLabel(item.documentStatus)
            }}</span>
          </td>
          <td class="p-3">
            <Button
              variant="outline"
              size="sm"
              @click="
                emit('navigate', {
                  kind: kind === 'executions' ? 'execution' : 'posting',
                  id: item.id,
                })
              "
              >{{
                kind === "executions"
                  ? "Открыть исполнение"
                  : "Открыть проводку"
              }}</Button
            >
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
