<script setup lang="ts">
import { Button } from "@/components/ui/button";
import type { CategoryOption } from "../../model/category.types";
defineProps<{ options: CategoryOption[]; disabled: boolean }>();
const emit = defineEmits<{
  edit: [row: CategoryOption];
  remove: [row: CategoryOption];
  makeDefault: [row: CategoryOption];
}>();
</script>
<template>
  <ul class="divide-y rounded-lg border">
    <li
      v-for="row in options"
      :key="row.id"
      class="flex flex-wrap items-center justify-between gap-2 px-3 py-2"
    >
      <div
        :style="{ paddingInlineStart: Math.min(8, row.depth) + 'rem' }"
        :title="row.path"
      >
        <span class="font-medium">{{ row.name ?? row.fallbackName }}</span>
        <span v-if="!row.name" class="ml-2 text-sm text-muted-foreground"
          >Нет перевода · {{ row.fallbackLocale }}</span
        >
        <span v-if="row.isDefault" class="ml-2 text-sm text-muted-foreground"
          >По умолчанию</span
        >
      </div>
      <div class="flex flex-wrap gap-1">
        <Button
          size="sm"
          variant="outline"
          :disabled="disabled"
          @click="emit('edit', row)"
          >Изменить</Button
        >
        <Button
          v-if="!row.isDefault"
          size="sm"
          variant="ghost"
          :disabled="disabled"
          @click="emit('makeDefault', row)"
          >По умолчанию</Button
        >
        <Button
          v-if="!row.isDefault"
          size="sm"
          variant="ghost"
          :disabled="disabled"
          @click="emit('remove', row)"
          >Удалить</Button
        >
      </div>
    </li>
  </ul>
</template>
