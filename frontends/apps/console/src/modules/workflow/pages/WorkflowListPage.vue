<script setup lang="ts">
import { computed, ref } from "vue";

import WorkflowApplicationsList from "@/modules/workflow/components/WorkflowApplicationsList.vue";
import { useWorkflowApplicationsInfiniteQuery } from "@/modules/workflow/queries/use-workflow-applications-infinite-query.ts";

const limit = ref(10);

const workflowApplicationsQuery = useWorkflowApplicationsInfiniteQuery(limit);

const errorMessage = computed(() => {
  return workflowApplicationsQuery.error.value?.message ?? null;
});
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
    <header
      class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between"
    >
      <div class="grid gap-1">
        <h2 class="text-lg font-semibold tracking-normal">
          Workflow applications
        </h2>
      </div>
    </header>

    <WorkflowApplicationsList
      :applications="workflowApplicationsQuery.items.value"
      :pending="workflowApplicationsQuery.isPending.value"
      :error-message="errorMessage"
      :refreshing="
        workflowApplicationsQuery.isFetching.value &&
        !workflowApplicationsQuery.isFetchingNextPage.value
      "
      :has-next-page="workflowApplicationsQuery.hasNextPage.value"
      :loading-more="workflowApplicationsQuery.isFetchingNextPage.value"
      :pagination-disabled="
        workflowApplicationsQuery.isFetching.value &&
        !workflowApplicationsQuery.isFetchingNextPage.value
      "
      :skeleton-count="limit"
      @load-more="workflowApplicationsQuery.loadMore()"
    />
  </section>
</template>
