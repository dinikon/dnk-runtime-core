import type { RouteRecordRaw } from "vue-router";
export const supplierSourcingRoutes: RouteRecordRaw[] = [
  {
    path: "supplier-sourcing/sources",
    name: "supplier-sources",
    component: () => import("./pages/SupplierSourcesPage.vue"),
  },
  {
    path: "supplier-sourcing/sources/:sourceId",
    name: "supplier-source",
    component: () => import("./pages/SupplierSourcePage.vue"),
  },
];
