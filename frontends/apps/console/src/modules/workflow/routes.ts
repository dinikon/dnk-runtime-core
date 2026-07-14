import type { RouteRecordRaw } from "vue-router";

import WorkflowApplicationsPage from "@/modules/workflow/applications/ui/page/WorkflowApplicationsPage.vue";
import WorkflowApplicationsRouteHeader from "@/modules/workflow/applications/ui/page/WorkflowApplicationsRouteHeader.vue";
import WorkflowPage from "@/modules/workflow/workflows/ui/page/WorkflowPage.vue";

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

export const workflowEditorRoutes: RouteRecordRaw[] = [
  {
    path: "",
    name: "workflow-editor",
    component: WorkflowPage,
    props: (route) => ({ id: String(route.params.id) }),
    meta: {
      title: "Workflow editor",
    },
  },
];
