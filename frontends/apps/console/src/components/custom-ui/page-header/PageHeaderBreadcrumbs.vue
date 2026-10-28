<script setup lang="ts">
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import type { PageHeaderBreadcrumb } from "./page-header.types";

defineProps<{ items: readonly PageHeaderBreadcrumb[] }>();
const emit = defineEmits<{ navigate: [item: PageHeaderBreadcrumb] }>();
</script>

<template>
  <Breadcrumb>
    <BreadcrumbList>
      <template v-for="(item, index) in items" :key="item.id">
        <BreadcrumbSeparator v-if="index > 0" />
        <BreadcrumbItem>
          <BreadcrumbPage v-if="index === items.length - 1">{{
            item.label
          }}</BreadcrumbPage>
          <BreadcrumbLink v-else as-child>
            <button type="button" @click="emit('navigate', item)">
              {{ item.label }}
            </button>
          </BreadcrumbLink>
        </BreadcrumbItem>
      </template>
    </BreadcrumbList>
  </Breadcrumb>
</template>
