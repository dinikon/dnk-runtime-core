<script setup lang="ts">
import { Trash2 } from "@lucide/vue";
import { Button } from "@/components/ui/button";
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
defineProps<{ items: FileItem[]; busy: boolean }>();
defineEmits<{ trash: [file: FileItem] }>();
</script>
<template>
  <div class="hidden md:block">
    <Table
      ><TableHeader
        ><TableRow
          ><TableHead>Название</TableHead><TableHead>Диск</TableHead
          ><TableHead>Размер</TableHead><TableHead>Дата загрузки</TableHead
          ><TableHead class="text-right">Действия</TableHead></TableRow
        ></TableHeader
      ><TableBody
        ><TableRow v-for="file in items" :key="file.file_id"
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
            ><Button
              variant="ghost"
              size="sm"
              :aria-label="`В корзину: ${file.name}`"
              :disabled="busy"
              @click="$emit('trash', file)"
              ><Trash2 data-icon="inline-start" />В корзину</Button
            ></TableCell
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
      <FileName :file="file" />
      <p class="break-all text-sm text-muted-foreground">
        {{ file.bucket_name }} · {{ formatStorageBytes(file.size_bytes) }}
      </p>
      <p class="text-xs text-muted-foreground">
        {{ formatFileDate(file.created_at) }}
      </p>
      <Button
        variant="outline"
        size="sm"
        :disabled="busy"
        :aria-label="`В корзину: ${file.name}`"
        @click="$emit('trash', file)"
        ><Trash2 data-icon="inline-start" />В корзину</Button
      >
    </article>
  </div>
</template>
