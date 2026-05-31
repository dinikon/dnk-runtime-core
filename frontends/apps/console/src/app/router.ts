import { createRouter, createWebHistory } from "vue-router";

import { getApiErrorStatus } from "@/app/providers/http";
import { useTenantStore } from "@/app/stores/tenant";
import { useUserStore } from "@/app/stores/user";
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
  const tenantStore = useTenantStore();
  const userStore = useUserStore();
  const isPublicRoute = to.meta.public === true;

  try {
    await userStore.loadCurrentUser();

    if (isPublicRoute) {
      return { name: "dashboard" };
    }

    if (!tenantStore.tenant) {
      await tenantStore.resolveTenant();
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
