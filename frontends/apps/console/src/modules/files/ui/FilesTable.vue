<script setup lang="ts">
import { Eye, Trash2 } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  formatStorageBytes,
  formatFileDate,
  type FileItem,
} from "../model/types";
import FileName from "./FileName.vue";
defineProps<{ items: FileItem[]; busy: boolean; selected: string[] }>();
defineEmits<{
  trash: [file: FileItem];
  preview: [file: FileItem];
  select: [id: string, checked: boolean];
}>();
</script>
<template>
  <div class="hidden md:block">
    <Table
      ><TableHeader
        ><TableRow
          ><TableHead class="w-10"><span class="sr-only">Выбор</span></TableHead
          ><TableHead>Название</TableHead><TableHead>Диск</TableHead
          ><TableHead>Размер</TableHead><TableHead>Дата загрузки</TableHead
          ><TableHead class="text-right">Действия</TableHead></TableRow
        ></TableHeader
      ><TableBody
        ><TableRow
          v-for="file in items"
          :key="file.file_id"
          :data-state="selected.includes(file.file_id) ? 'selected' : undefined"
          ><TableCell
            ><Checkbox
              :model-value="selected.includes(file.file_id)"
              :disabled="busy"
              :aria-label="`Выбрать: ${file.name}`"
              @update:model-value="
                $emit('select', file.file_id, $event === true)
              " /></TableCell
          ><TableCell class="max-w-72"><FileName :file="file" /></TableCell
          ><TableCell class="max-w-48 truncate" :title="file.bucket_name">{{
            file.bucket_name
          }}</TableCell
          ><TableCell class="whitespace-nowrap tabular-nums">{{
            formatStorageBytes(file.size_bytes)
          }}</TableCell
          ><TableCell class="whitespace-nowrap">{{
            formatFileDate(file.created_at)
          }}</TableCell
          ><TableCell class="text-right"
            ><div class="flex justify-end gap-1">
              <Button
                variant="ghost"
                size="sm"
                :aria-label="`Предпросмотр: ${file.name}`"
                :disabled="busy"
                @click="$emit('preview', file)"
                ><Eye data-icon="inline-start" />Предпросмотр</Button
              ><Button
                variant="ghost"
                size="sm"
                :aria-label="`В корзину: ${file.name}`"
                :disabled="busy"
                @click="$emit('trash', file)"
                ><Trash2 data-icon="inline-start" />В корзину</Button
              >
            </div></TableCell
          ></TableRow
        ></TableBody
      ></Table
    >
  </div>
  <div class="flex flex-col gap-3 md:hidden">
    <article
      v-for="file in items"
      :key="file.file_id"
      class="flex min-w-0 flex-col gap-3 rounded-lg border p-4"
    >
      <div class="flex min-w-0 items-start gap-3">
        <Checkbox
          :model-value="selected.includes(file.file_id)"
          :disabled="busy"
          :aria-label="`Выбрать: ${file.name}`"
          @update:model-value="$emit('select', file.file_id, $event === true)"
        /><FileName class="min-w-0" :file="file" />
      </div>
      <p class="break-all text-sm text-muted-foreground">
        {{ file.bucket_name }} · {{ formatStorageBytes(file.size_bytes) }}
      </p>
      <p class="text-xs text-muted-foreground">
        {{ formatFileDate(file.created_at) }}
      </p>
      <div class="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          :disabled="busy"
          :aria-label="`Предпросмотр: ${file.name}`"
          @click="$emit('preview', file)"
          ><Eye data-icon="inline-start" />Предпросмотр</Button
        ><Button
          variant="outline"
          size="sm"
          :disabled="busy"
          :aria-label="`В корзину: ${file.name}`"
          @click="$emit('trash', file)"
          ><Trash2 data-icon="inline-start" />В корзину</Button
        >
      </div>
    </article>
  </div>
</template>
