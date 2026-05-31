import { createRouter, createWebHistory } from "vue-router";

import { useSessionStore } from "@/app/stores/session";
import { ContactsPage } from "@/modules/crm";
import LoginPage from "@/modules/auth/pages/LoginPage.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/crm/contacts",
    },
    {
      path: "/login",
      name: "login",
      component: LoginPage,
      meta: {
        public: true,
      },
    },
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
