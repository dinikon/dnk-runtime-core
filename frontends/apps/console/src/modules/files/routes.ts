import type { RouteRecordRaw } from "vue-router";
export const filesRoutes: RouteRecordRaw[] = [
  {
    path: "files",
    name: "admin-files",
    component: () => import("./pages/FilesPage.vue"),
  },
  {
    path: "files/trash",
    name: "admin-files-trash",
    component: () => import("./pages/FilesPage.vue"),
  },
  {
    path: "files/disks",
    name: "admin-files-disks",
    component: () => import("./pages/FilesPage.vue"),
  },
];
