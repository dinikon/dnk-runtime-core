import { createRouter, createWebHistory } from "vue-router";

import { getApiErrorStatus } from "@/app/providers/http";
import { useSessionStore } from "@/app/stores/session";
import { authRoutes } from "@/modules/auth/routes";
import { dashboardRoutes } from "@/modules/dashboard";
import { ContactsPage } from "@/modules/crm";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...dashboardRoutes,
    ...authRoutes,
    {
      path: "/crm/contacts",
      name: "crm-contacts",
      component: ContactsPage,
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
