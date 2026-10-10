import type { RouteRecordRaw } from "vue-router";
export const filesRoutes: RouteRecordRaw[] = [
  {
    path: "files",
    name: "files",
    component: () => import("./pages/FileStoragePage.vue"),
  },
];
