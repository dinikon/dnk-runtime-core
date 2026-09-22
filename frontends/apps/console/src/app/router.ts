import { createRouter, createWebHistory } from "vue-router";

import { AppLayout } from "@/layouts";
import { authRoutes } from "@/modules/auth/routes";
import { crmRoutes } from "@/modules/crm";
import { dashboardRoutes } from "@/modules/dashboard";
import { priceListRoutes } from "@/modules/price-lists";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...authRoutes,
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
      children: [
        {
          path: "",
          redirect: { name: "dashboard" },
        },
        ...dashboardRoutes,
        ...crmRoutes,
        ...priceListRoutes,
        {
          path: "settings/members",
          name: "members",
          component: () => import("@/modules/access/pages/MembersPage.vue"),
        },
        {
          path: "settings/account",
          name: "account",
          component: () => import("@/modules/access/pages/AccountPage.vue"),
        },
      ],
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/dashboard",
    },
  ],
});
