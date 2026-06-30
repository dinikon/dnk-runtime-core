<script setup lang="ts">
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { WorkflowApplicationListItem } from "@/modules/workflow/model/workflow-application.types.ts";
import { CursorPagination } from "@/shared/pagination";
import WorkflowApplicationsEmpty from "@/modules/workflow/components/WorkflowApplicationsEmpty.vue";
import WorkflowApplicationsResult from "@/modules/workflow/components/WorkflowApplicationsResult.vue";
import WorkflowApplicationsSkeleton from "@/modules/workflow/components/WorkflowApplicationsSkeleton.vue";

withDefaults(
  defineProps<{
    applications: WorkflowApplicationListItem[];
    pending: boolean;
    errorMessage?: string | null;
    refreshing: boolean;
    hasNextPage: boolean;
    loadingMore: boolean;
    paginationDisabled: boolean;
    skeletonCount?: number;
  }>(),
  {
    errorMessage: null,
    skeletonCount: 10,
  },
);

const emit = defineEmits<{
  (event: "loadMore"): void;
}>();
</script>

<template>
  <div class="min-h-0 flex-1 overflow-y-auto pr-1">
    <Alert v-if="errorMessage" variant="destructive">
      <AlertDescription>
        {{ errorMessage }}
      </AlertDescription>
    </Alert>

    <WorkflowApplicationsSkeleton v-else-if="pending" :count="skeletonCount" />

    <template v-else>
      <p v-if="refreshing" class="mb-3 text-sm text-muted-foreground">
        Background fetching...
      </p>

      <WorkflowApplicationsEmpty v-if="applications.length === 0" />

      <template v-else>
        <WorkflowApplicationsResult :applications="applications" />

        <CursorPagination
          :has-more="hasNextPage"
          :loading="loadingMore"
          :disabled="paginationDisabled"
          mode="infinite"
          loading-text="Loading more..."
          load-more-text="Load more"
          end-text="Nothing more to load"
          @load-more="emit('loadMore')"
        />
      </template>
    </template>
  </div>
</template>
