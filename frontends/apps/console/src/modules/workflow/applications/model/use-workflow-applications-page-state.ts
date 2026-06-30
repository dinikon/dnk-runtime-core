import { ref } from "vue";

export type WorkflowApplicationsViewMode = "cards";

export type WorkflowApplicationsPaginationMode = "infinite";

export function useWorkflowApplicationsPageState() {
  const viewMode = ref<WorkflowApplicationsViewMode>("cards");
  const paginationMode = ref<WorkflowApplicationsPaginationMode>("infinite");
  const limit = ref(12);

  return {
    viewMode,
    paginationMode,
    limit,
  };
}
