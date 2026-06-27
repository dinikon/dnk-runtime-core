import type { RouteRecordRaw } from "vue-router";

import WorkflowHeader from "@/modules/workflow/components/WorkflowHeader.vue";
import WorkflowListPage from "@/modules/workflow/pages/WorkflowListPage.vue";

export const workflowRoutes: RouteRecordRaw[] = [
  {
    path: "workflows",
    name: "workflow-list",
    components: {
      default: WorkflowListPage,
      header: WorkflowHeader,
    },
    meta: {
      title: "Workflows",
    },
  },
];
