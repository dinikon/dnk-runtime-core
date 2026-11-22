<script setup lang="ts">
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { FeedPreview } from "../../model/feed-preview.types";

defineProps<{ preview: FeedPreview }>();
defineEmits<{ openPublication: [id: string] }>();
</script>

<template>
  <Table class="border">
    <TableHeader>
      <TableRow>
        <TableHead scope="col">Публикация</TableHead>
        <TableHead
          v-for="column in preview.columns"
          :key="column.fieldId"
          scope="col"
        >
          {{ column.name }}
        </TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      <TableRow v-for="row in preview.rows" :key="row.publicationId">
        <TableCell class="align-top">
          <button
            type="button"
            class="text-left underline underline-offset-4"
            @click="$emit('openPublication', row.publicationId)"
          >
            {{ row.sku ?? row.variantId ?? row.itemId }}
          </button>
          <p
            v-for="(issue, index) in row.issues.filter(
              (item) =>
                !preview.columns.some(
                  (column) => column.fieldId === item.fieldId,
                ),
            )"
            :key="index"
            class="mt-1 max-w-64 whitespace-normal text-sm text-destructive"
          >
            {{ issue.message }}
          </p>
        </TableCell>
        <TableCell
          v-for="(column, index) in preview.columns"
          :key="column.fieldId"
          class="min-w-28 max-w-80 whitespace-pre-wrap break-words align-top"
        >
          <span v-if="row.values[index] !== null">{{ row.values[index] }}</span>
          <span
            v-else
            class="text-muted-foreground"
            aria-label="Пустое значение"
            >—</span
          >
          <p
            v-for="(issue, issueIndex) in row.issues.filter(
              (item) => item.fieldId === column.fieldId,
            )"
            :key="issueIndex"
            class="mt-1 text-sm text-destructive"
          >
            {{ issue.message }}
          </p>
        </TableCell>
      </TableRow>
    </TableBody>
  </Table>
</template>
