<script setup lang="ts">
import { computed, ref } from "vue";
import { toast } from "vue-sonner";

import { getApiErrorMessage } from "@/app/providers/http";
import { useCreateWorkflowApplication } from "@/modules/workflow/applications/model/use-create-workflow-application.ts";
import { useUpdateWorkflowApplication } from "@/modules/workflow/applications/model/use-update-workflow-application.ts";
import { useWorkflowApplicationsPageState } from "@/modules/workflow/applications/model/use-workflow-applications-page-state.ts";
import { useWorkflowApplicationsQuery } from "@/modules/workflow/applications/model/use-workflow-applications-query.ts";
import type {
  CreateWorkflowApplicationPayload,
  WorkflowApplicationListItem,
  WorkflowApplicationMutationPayload,
} from "@/modules/workflow/applications/model/workflow-application.types.ts";
import WorkflowApplicationCreationDialog from "@/modules/workflow/applications/ui/mutation/WorkflowApplicationCreationDialog.vue";
import WorkflowApplicationUpdateDialog from "@/modules/workflow/applications/ui/mutation/WorkflowApplicationUpdateDialog.vue";
import WorkflowApplicationsNavigationPanel from "@/modules/workflow/applications/ui/page/WorkflowApplicationsNavigationPanel.vue";
import WorkflowApplicationsPageHeader from "@/modules/workflow/applications/ui/page/WorkflowApplicationsPageHeader.vue";
import WorkflowApplicationsViewState from "@/modules/workflow/applications/ui/view-state/WorkflowApplicationsViewState.vue";

const pageState = useWorkflowApplicationsPageState();
const workflowApplicationsQuery = useWorkflowApplicationsQuery(pageState.limit);
const createWorkflowApplicationMutation = useCreateWorkflowApplication();
const updateWorkflowApplicationMutation = useUpdateWorkflowApplication();
const createOpen = ref(false);
const updateOpen = ref(false);
const selectedApplication = ref<WorkflowApplicationListItem | null>(null);

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

async function createWorkflowApplication(
  payload: CreateWorkflowApplicationPayload,
) {
  try {
    const workflow =
      await createWorkflowApplicationMutation.mutateAsync(payload);

    createOpen.value = false;
    toast.success(`${workflow.title} created.`);
  } catch (error) {
    toast.error(
      getApiErrorMessage(error, "Failed to create workflow application."),
    );
  }
}

function editWorkflowApplication(application: WorkflowApplicationListItem) {
  selectedApplication.value = application;
  updateOpen.value = true;
}

function setUpdateOpen(open: boolean) {
  updateOpen.value = open;

  if (!open) {
    selectedApplication.value = null;
  }
}

async function updateWorkflowApplication(
  payload: WorkflowApplicationMutationPayload,
) {
  const application = selectedApplication.value;

  if (application === null) {
    return;
  }

  try {
    const workflow = await updateWorkflowApplicationMutation.mutateAsync({
      id: application.id,
      ...payload,
    });

    updateOpen.value = false;
    selectedApplication.value = null;
    toast.success(`${workflow.title} saved.`);
  } catch (error) {
    toast.error(
      getApiErrorMessage(error, "Failed to update workflow application."),
    );
  }
}
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
    <WorkflowApplicationsPageHeader @create="createOpen = true" />

    <div class="min-h-0 flex-1 overflow-y-auto pr-1">
      <WorkflowApplicationsViewState
        :items="workflowApplicationsQuery.items.value"
        :loading="workflowApplicationsQuery.isPending.value"
        :error-message="errorMessage"
        :fetching="backgroundFetching"
        :view-mode="pageState.viewMode.value"
        :skeleton-count="pageState.limit.value"
        @edit="editWorkflowApplication"
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

    <WorkflowApplicationCreationDialog
      v-model:open="createOpen"
      :saving="createWorkflowApplicationMutation.isPending.value"
      @submit="createWorkflowApplication"
    />

    <WorkflowApplicationUpdateDialog
      :open="updateOpen"
      :saving="updateWorkflowApplicationMutation.isPending.value"
      :application="selectedApplication"
      @update:open="setUpdateOpen"
      @submit="updateWorkflowApplication"
    />
  </section>
</template>
