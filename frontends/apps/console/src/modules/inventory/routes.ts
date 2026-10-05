import type { RouteRecordRaw } from "vue-router";
export const inventoryRoutes: RouteRecordRaw[] = [
  {
    path: "inventory/skus",
    name: "inventory-skus",
    component: () => import("./pages/SkusPage.vue"),
  },
  {
    path: "inventory/skus/new",
    name: "inventory-sku-new",
    component: () => import("./pages/CreateSkuPage.vue"),
  },
  {
    path: "inventory/skus/:skuId",
    name: "inventory-sku",
    component: () => import("./pages/SkuPage.vue"),
  },
];
