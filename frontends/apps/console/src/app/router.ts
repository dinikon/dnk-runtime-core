import { createRouter, createWebHistory } from "vue-router";

import { AppLayout } from "@/layouts";
import { authRoutes } from "@/modules/auth/routes";
import { communicationRoutes } from "@/modules/communication";
import { dashboardRoutes } from "@/modules/dashboard";
import { workflowRoutes } from "@/modules/workflow";

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
        ...workflowRoutes,
        ...communicationRoutes,
      ],
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: { name: "dashboard" },
    },
  ],
});
