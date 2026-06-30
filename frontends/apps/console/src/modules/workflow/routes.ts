import type { RouteRecordRaw } from "vue-router";

import WorkflowApplicationsPage from "@/modules/workflow/applications/ui/page/WorkflowApplicationsPage.vue";
import WorkflowApplicationsRouteHeader from "@/modules/workflow/applications/ui/page/WorkflowApplicationsRouteHeader.vue";

export const workflowRoutes: RouteRecordRaw[] = [
  {
    path: "workflows",
    name: "workflow-list",
    components: {
      default: WorkflowApplicationsPage,
      header: WorkflowApplicationsRouteHeader,
    },
    meta: {
      title: "Workflows",
    },
  },
];
