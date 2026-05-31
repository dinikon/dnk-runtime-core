import type { RouteRecordRaw } from "vue-router";

import DashboardHeader from "@/modules/dashboard/components/DashboardHeader.vue";
import DashboardPage from "@/modules/dashboard/pages/DashboardPage.vue";

export const dashboardRoutes: RouteRecordRaw[] = [
  {
    path: "dashboard",
    name: "dashboard",
    components: {
      default: DashboardPage,
      header: DashboardHeader,
    },
  },
];
