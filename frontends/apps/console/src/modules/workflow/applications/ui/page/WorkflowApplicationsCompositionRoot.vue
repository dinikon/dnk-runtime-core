<script setup lang="ts">
import { computed } from "vue";

import { useWorkflowApplicationsPageState } from "@/modules/workflow/applications/model/use-workflow-applications-page-state.ts";
import { useWorkflowApplicationsQuery } from "@/modules/workflow/applications/model/use-workflow-applications-query.ts";
import WorkflowApplicationsNavigationPanel from "@/modules/workflow/applications/ui/page/WorkflowApplicationsNavigationPanel.vue";
import WorkflowApplicationsPageHeader from "@/modules/workflow/applications/ui/page/WorkflowApplicationsPageHeader.vue";
import WorkflowApplicationsViewState from "@/modules/workflow/applications/ui/view-state/WorkflowApplicationsViewState.vue";

const pageState = useWorkflowApplicationsPageState();
const workflowApplicationsQuery = useWorkflowApplicationsQuery(pageState.limit);

const errorMessage = computed(() => {
  return workflowApplicationsQuery.error.value?.message ?? null;
});

const backgroundFetching = computed(() => {
  return (
    workflowApplicationsQuery.isFetching.value &&
    !workflowApplicationsQuery.isFetchingNextPage.value
  );
});

const showNavigationPanel = computed(() => {
  return (
    !workflowApplicationsQuery.isPending.value &&
    !errorMessage.value &&
    workflowApplicationsQuery.items.value.length > 0
  );
});
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
    <WorkflowApplicationsPageHeader />

    <div class="min-h-0 flex-1 overflow-y-auto pr-1">
      <WorkflowApplicationsViewState
        :items="workflowApplicationsQuery.items.value"
        :loading="workflowApplicationsQuery.isPending.value"
        :error-message="errorMessage"
        :fetching="backgroundFetching"
        :view-mode="pageState.viewMode.value"
        :skeleton-count="pageState.limit.value"
      />

      <WorkflowApplicationsNavigationPanel
        v-if="showNavigationPanel"
        :pagination-mode="pageState.paginationMode.value"
        :has-more="workflowApplicationsQuery.hasNextPage.value"
        :loading="workflowApplicationsQuery.isFetchingNextPage.value"
        :disabled="backgroundFetching"
        @load-more="workflowApplicationsQuery.loadMore()"
      />
    </div>
  </section>
</template>
