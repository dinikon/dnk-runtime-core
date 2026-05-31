import { createRouter, createWebHistory } from "vue-router";

import { getApiErrorStatus } from "@/app/providers/http";
import { useSessionStore } from "@/app/stores/session";
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

router.beforeEach(async (to) => {
  const sessionStore = useSessionStore();
  const isPublicRoute = to.meta.public === true;

  try {
    await sessionStore.loadCurrentUser();

    if (isPublicRoute) {
      return { name: "dashboard" };
    }

    return true;
  } catch (error) {
    if (isPublicRoute || getApiErrorStatus(error) !== 401) {
      return true;
    }

    return {
      name: "login",
      query: {
        redirect: to.fullPath,
      },
    };
  }
});
