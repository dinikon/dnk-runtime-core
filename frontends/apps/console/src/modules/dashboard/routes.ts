import type { RouteRecordRaw } from "vue-router";

import DashboardPage from "@/modules/dashboard/pages/DashboardPage.vue";

export const dashboardRoutes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "dashboard",
    component: DashboardPage,
  },
];
