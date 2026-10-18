import type { RouteRecordRaw } from "vue-router";
export const catalogRoutes: RouteRecordRaw[] = [
  { path: "catalog", redirect: "/catalog/items" },
  {
    path: "catalog/items",
    component: () => import("./ui/page/CatalogItemsPage.vue"),
  },
  {
    path: "catalog/items/new",
    component: () => import("./ui/page/CatalogItemCreatePage.vue"),
  },
  {
    path: "catalog/items/:itemId",
    component: () => import("./ui/page/CatalogItemOverviewPage.vue"),
  },
  {
    path: "catalog/items/:itemId/edit",
    component: () => import("./ui/page/CatalogItemEditorPage.vue"),
  },
];
