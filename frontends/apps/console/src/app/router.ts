import { createRouter, createWebHistory } from "vue-router";

import { AppLayout } from "@/layouts";
import { authRoutes } from "@/modules/auth/routes";
import { crmRoutes } from "@/modules/crm";
import { dashboardRoutes } from "@/modules/dashboard";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...authRoutes,
    {
      path: "/",
      component: AppLayout,
      children: [
        {
          path: "",
          redirect: { name: "dashboard" },
        },
        ...dashboardRoutes,
        ...crmRoutes,
      ],
    },
  ],
});
