<script setup lang="ts">
import type { WorkflowApplicationsViewMode } from "@/modules/workflow/applications/model/use-workflow-applications-page-state.ts";
import type { WorkflowApplicationListItem } from "@/modules/workflow/applications/model/workflow-application.types.ts";
import WorkflowApplicationsEmptyState from "@/modules/workflow/applications/ui/view-state/WorkflowApplicationsEmptyState.vue";
import WorkflowApplicationsErrorState from "@/modules/workflow/applications/ui/view-state/WorkflowApplicationsErrorState.vue";
import WorkflowApplicationsLoadingState from "@/modules/workflow/applications/ui/view-state/WorkflowApplicationsLoadingState.vue";
import WorkflowApplicationsResultSet from "@/modules/workflow/applications/ui/view-state/WorkflowApplicationsResultSet.vue";

withDefaults(
  defineProps<{
    items: WorkflowApplicationListItem[];
    loading: boolean;
    errorMessage?: string | null;
    fetching: boolean;
    viewMode: WorkflowApplicationsViewMode;
    skeletonCount?: number;
  }>(),
  {
    errorMessage: null,
    skeletonCount: 10,
  },
);

const emit = defineEmits<{
  (event: "open", value: WorkflowApplicationListItem): void;
  (event: "edit", value: WorkflowApplicationListItem): void;
}>();
</script>

<template>
  <div class="grid gap-3">
    <WorkflowApplicationsErrorState
      v-if="errorMessage"
      :message="errorMessage"
    />

    <WorkflowApplicationsLoadingState
      v-else-if="loading"
      :count="skeletonCount"
    />

    <template v-else>
      <p v-if="fetching" class="text-sm text-muted-foreground">
        Background fetching...
      </p>

      <WorkflowApplicationsEmptyState v-if="items.length === 0" />

      <WorkflowApplicationsResultSet
        v-else
        :items="items"
        :view-mode="viewMode"
        @open="emit('open', $event)"
        @edit="emit('edit', $event)"
      />
    </template>
  </div>
</template>
