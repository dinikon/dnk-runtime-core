import type { RouteRecordRaw } from "vue-router";
export const funnelRoutes: RouteRecordRaw[] = [
  {
    path: "funnels",
    name: "funnels",
    component: () => import("./pages/FunnelsPage.vue"),
  },
  {
    path: "funnels/new",
    name: "funnel-new",
    component: () => import("./pages/FunnelEditorPage.vue"),
  },
  {
    path: "funnels/:id",
    name: "funnel-detail",
    component: () => import("./pages/FunnelEditorPage.vue"),
  },
];
