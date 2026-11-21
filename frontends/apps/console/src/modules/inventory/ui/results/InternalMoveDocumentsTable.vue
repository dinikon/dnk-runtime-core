<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { internalMoveStatusLabels } from "../../model/internal-move-page-state";
import type { InternalMoveListItem } from "../../model/internal-move.types";
defineProps<{ items: readonly InternalMoveListItem[] }>();
const emit = defineEmits<{ open: [id: string] }>();
</script>
<template>
  <div class="overflow-x-auto rounded-md border">
    <table class="w-full text-left text-sm">
      <thead class="bg-muted">
        <tr>
          <th class="p-3">Перемещение</th>
          <th class="p-3">Статус</th>
          <th class="p-3">Склад / владелец</th>
          <th class="p-3">Строк</th>
          <th class="p-3">Создано</th>
          <th class="p-3"><span class="sr-only">Действия</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id" class="border-t">
          <td class="p-3 font-mono text-xs">{{ item.id }}</td>
          <td class="p-3">{{ internalMoveStatusLabels[item.status] }}</td>
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
