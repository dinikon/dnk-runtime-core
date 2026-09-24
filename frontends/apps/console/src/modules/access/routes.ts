import type { RouteRecordRaw } from "vue-router";

export const accessRoutes: RouteRecordRaw[] = [
  {
    path: "users",
    name: "admin-users",
    component: () => import("./pages/UsersPage.vue"),
  },
];
