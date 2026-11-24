<script setup lang="ts">
import { computed } from "vue";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { FeedPreview } from "../../model/feed-preview.types";

const props = defineProps<{ preview: FeedPreview }>();
const hasCategories = computed(() => props.preview.rows.some(row => row.categories?.length));
defineEmits<{ openPublication: [id: string] }>();
</script>

<template>
  <Table class="border">
    <TableHeader>
      <TableRow>
        <TableHead scope="col">Публикация</TableHead>
        <TableHead v-if="hasCategories" scope="col">Категория</TableHead>
        <TableHead
          v-for="column in preview.columns"
          :key="column.fieldId"
          scope="col"
          :title="column.xmlAttribute ? 'Атрибут XML-предложения' : undefined"
        >
          {{ column.xmlAttribute ? `@${column.name}` : column.name }}
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
        <TableCell v-if="hasCategories" class="min-w-48 align-top">
          <div v-for="category in row.categories" :key="category.fieldId" class="mb-2 last:mb-0">
            <p class="text-sm font-medium">{{ category.fieldLabel }}</p>
            <p>{{ category.path.join(" / ") }} · #{{ category.exportId }}</p>
            <p v-if="category.ruleLabel" class="text-sm text-muted-foreground">{{ category.ruleLabel }}</p>
          </div>
          <span v-if="!row.categories?.length">—</span>
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
