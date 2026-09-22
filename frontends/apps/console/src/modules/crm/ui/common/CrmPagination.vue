<script setup lang="ts">
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";

defineProps<{ page: number; total: number; pageSize: number }>();
defineEmits<{ "update:page": [value: number] }>();
</script>

<template>
  <Pagination
    v-if="total > pageSize"
    :page="page"
    :total="total"
    :items-per-page="pageSize"
    :sibling-count="1"
    show-edges
    @update:page="$emit('update:page', $event)"
  >
    <PaginationContent v-slot="{ items }">
      <PaginationPrevious />
      <template v-for="(item, index) in items" :key="index">
        <PaginationItem
          v-if="item.type === 'page'"
          :value="item.value"
          :is-active="item.value === page"
        >
          {{ item.value }}
        </PaginationItem>
        <PaginationEllipsis v-else :index="index" />
      </template>
      <PaginationNext />
    </PaginationContent>
  </Pagination>
</template>
