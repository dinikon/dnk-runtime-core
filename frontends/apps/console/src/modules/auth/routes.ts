import type { RouteRecordRaw } from "vue-router";

import LoginPage from "@/modules/auth/pages/LoginPage.vue";

export const authRoutes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: LoginPage,
    meta: {
      public: true,
    },
  },
];
