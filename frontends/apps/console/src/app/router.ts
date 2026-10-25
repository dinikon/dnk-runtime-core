import type { Pinia } from "pinia";
import { createRouter, createWebHistory } from "vue-router";

import { useUserStore } from "@/app/stores/user";
import { requestsCloudLogin, withoutAuthProvider } from "@/modules/auth";
import { AdminLayout, AppLayout } from "@/layouts";
import { accessRoutes } from "@/modules/access/routes";
import { authRoutes } from "@/modules/auth/routes";
import { catalogRoutes } from "@/modules/catalog/routes";
import { filesRoutes } from "@/modules/files/routes";
import { funnelRoutes } from "@/modules/funnel";
import { crmRoutes } from "@/modules/crm";
import { dashboardRoutes } from "@/modules/dashboard";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...authRoutes,
    {
      path: "/files",
      redirect: (to) => ({ name: "admin-files", query: to.query }),
    },
    {
      path: "/accept-invitation",
      name: "accept-invitation",
      component: () =>
        import("@/modules/access/pages/AcceptInvitationPage.vue"),
      meta: { public: true },
    },
    {
      path: "/",
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: "",
          redirect: { name: "dashboard" },
        },
        ...dashboardRoutes,
        ...catalogRoutes,
        ...crmRoutes,
        ...funnelRoutes,
        {
          path: "settings/members",
          redirect: { name: "admin-users" },
        },
        {
          path: "settings/account",
          name: "account",
          component: () => import("@/modules/access/pages/AccountPage.vue"),
        },
      ],
    },
    {
      path: "/admin",
      component: AdminLayout,
      meta: { requiresAuth: true, requiredRole: "admin" },
      children: [
        {
          path: "",
          redirect: { name: "admin-users" },
        },
        ...accessRoutes,
        ...filesRoutes,
        {
          path: "contact-points",
          name: "admin-contact-points",
          component: () =>
            import("@/modules/contact-points/pages/ContactPointSettingsPage.vue"),
        },
      ],
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/dashboard",
    },
  ],
});

export function installRouterGuards(pinia: Pinia) {
  router.beforeEach(async (to) => {
    if (!to.matched.some((record) => record.meta.requiresAuth)) {
      return true;
    }

    const userStore = useUserStore(pinia);

    try {
      await userStore.ensureCurrentUser();
    } catch {
      return {
        name: "login",
        query: {
          redirect: withoutAuthProvider(to.fullPath),
          ...(requestsCloudLogin(to.query.auth_provider)
            ? { auth_provider: "cloud" }
            : {}),
        },
      };
    }

    if (to.query.auth_provider !== undefined) {
      return withoutAuthProvider(to.fullPath);
    }

    const requiredRole = [...to.matched]
      .reverse()
      .map((record) => record.meta.requiredRole)
      .find((role) => role !== undefined);

    if (requiredRole && userStore.user?.role !== requiredRole) {
      return { name: "dashboard" };
    }

    return true;
  });
}
