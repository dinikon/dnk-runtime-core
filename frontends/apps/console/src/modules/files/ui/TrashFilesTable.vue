<script setup lang="ts">
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
  type TrashFileItem,
} from "../model/types";
import FileName from "./FileName.vue";
import TrashFileActions from "./TrashFileActions.vue";
defineProps<{ items: TrashFileItem[]; busy: boolean }>();
defineEmits<{ restore: [file: TrashFileItem]; purge: [file: TrashFileItem] }>();
</script>
<template>
  <div class="hidden xl:block">
    <Table
      ><TableHeader
        ><TableRow
          ><TableHead>Название / диск</TableHead><TableHead>Размер</TableHead
          ><TableHead>Удалён</TableHead><TableHead>Хранится до</TableHead
          ><TableHead>Действия</TableHead></TableRow
        ></TableHeader
      ><TableBody
        ><TableRow v-for="file in items" :key="file.file_id"
          ><TableCell class="max-w-64"
            ><FileName :file="file" />
            <p
              class="mt-1 truncate text-xs text-muted-foreground"
              :title="file.bucket_name"
            >
              {{ file.bucket_name }}
            </p></TableCell
          ><TableCell class="whitespace-nowrap">{{
            formatStorageBytes(file.size_bytes)
          }}</TableCell
          ><TableCell class="whitespace-nowrap">{{
            formatFileDate(file.deleted_at)
          }}</TableCell
          ><TableCell class="whitespace-nowrap">{{
            formatFileDate(file.purge_after)
          }}</TableCell
          ><TableCell
            ><TrashFileActions
              :file="file"
              :busy="busy"
              @restore="$emit('restore', $event)"
              @purge="
                $emit('purge', $event)
              " /></TableCell></TableRow></TableBody
    ></Table>
  </div>
  <div class="flex flex-col gap-3 xl:hidden">
    <article
      v-for="file in items"
      :key="file.file_id"
      class="flex min-w-0 flex-col gap-3 rounded-lg border p-4"
    >
      <FileName :file="file" />
      <p class="break-all text-sm text-muted-foreground">
        {{ file.bucket_name }} · {{ formatStorageBytes(file.size_bytes) }}
      </p>
      <dl class="grid gap-1 text-xs">
        <div>Удалён: {{ formatFileDate(file.deleted_at) }}</div>
        <div>Хранится до: {{ formatFileDate(file.purge_after) }}</div>
      </dl>
      <TrashFileActions
        :file="file"
        :busy="busy"
        @restore="$emit('restore', $event)"
        @purge="$emit('purge', $event)"
      />
    </article>
  </div>
</template>
