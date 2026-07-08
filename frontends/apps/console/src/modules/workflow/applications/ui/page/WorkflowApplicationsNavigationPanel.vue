<script setup lang="ts">
import type { WorkflowApplicationsPaginationMode } from "@/modules/workflow/applications/model/use-workflow-applications-page-state.ts";
import { CursorPagination } from "@/shared/pagination";

withDefaults(
  defineProps<{
    paginationMode: WorkflowApplicationsPaginationMode;
    hasMore: boolean;
    loading?: boolean;
    disabled?: boolean;
  }>(),
  {
    loading: false,
    disabled: false,
  },
);

const emit = defineEmits<{
  (event: "loadMore"): void;
}>();
</script>

<template>
  <CursorPagination
    v-if="paginationMode === 'infinite'"
    :has-more="hasMore"
    :loading="loading"
    :disabled="disabled"
    mode="infinite"
    loading-text="Loading more..."
    load-more-text="Load more"
    end-text="Nothing more to load"
    @load-more="emit('loadMore')"
  />
</template>
