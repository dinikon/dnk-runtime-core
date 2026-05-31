import { createRouter, createWebHistory } from "vue-router";

import { useSessionStore } from "@/app/stores/session";
import { authRoutes } from "@/modules/auth/routes";
import { ContactsPage } from "@/modules/crm";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/crm/contacts",
    },
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

  if (!sessionStore.isAuthenticated) {
    await sessionStore.loadCurrentUser();
  }

  if (isPublicRoute && sessionStore.isAuthenticated) {
    return "/";
  }

  if (!isPublicRoute && !sessionStore.isAuthenticated) {
    return {
      name: "login",
      query: {
        redirect: to.fullPath,
      },
    };
  }

  return true;
});
