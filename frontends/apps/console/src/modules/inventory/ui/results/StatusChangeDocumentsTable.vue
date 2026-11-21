<script setup lang="ts">
import { stockStatusLabel } from "../../model/stock-accounting.constants";
import { Button } from "@/components/ui/button";
import { statusChangeStatusLabels } from "../../model/status-change-page-state";
import type { StatusChangeListItem } from "../../model/status-change.types";
defineProps<{ items: readonly StatusChangeListItem[] }>();
const emit = defineEmits<{ open: [id: string] }>();
</script>
<template>
  <div class="overflow-x-auto rounded-md border">
    <table class="w-full text-left text-sm">
      <thead class="bg-muted">
        <tr>
          <th class="p-3">Изменение состояния</th>
          <th class="p-3">Статус</th>
          <th class="p-3">Новое состояние</th>
          <th class="p-3">Причина</th>
          <th class="p-3">Склад / владелец</th>
          <th class="p-3">Строк</th>
          <th class="p-3">Создано</th>
          <th class="p-3"><span class="sr-only">Действия</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id" class="border-t">
          <td class="p-3 font-mono text-xs">{{ item.id }}</td>
          <td class="p-3">{{ statusChangeStatusLabels[item.status] }}</td>
          <td class="p-3">{{ stockStatusLabel(item.targetStatus) }}</td>
          <td class="max-w-72 p-3">
            <p
              class="line-clamp-2 whitespace-pre-wrap break-words"
              :title="item.reason"
            >
              {{ item.reason }}
            </p>
          </td>
          <td class="p-3">
            <p>{{ item.warehouseCode }} — {{ item.warehouseName }}</p>
            <p class="text-muted-foreground">
              {{ item.ownerName ?? "Компания недоступна" }}
            </p>
          </td>
          <td class="p-3">{{ item.lineCount }}</td>
          <td class="p-3">
            <time :datetime="item.createdAt">{{
              new Date(item.createdAt).toLocaleString()
            }}</time>
          </td>
          <td class="p-3">
            <Button variant="outline" size="sm" @click="emit('open', item.id)"
              >Открыть</Button
            >
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
