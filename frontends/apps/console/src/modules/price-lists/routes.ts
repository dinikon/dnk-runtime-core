import type { RouteRecordRaw } from "vue-router";

export const priceListRoutes: RouteRecordRaw[] = [
  {
    path: "purchases/price-lists",
    name: "price-lists",
    component: () => import("./pages/PriceListsPage.vue"),
  },
  {
    path: "purchases/price-lists/new",
    name: "price-list-new",
    component: () => import("./pages/PriceListWizardPage.vue"),
  },
  {
    path: "purchases/price-lists/:id",
    name: "price-list-detail",
    component: () => import("./pages/PriceListDetailPage.vue"),
  },
  {
    path: "purchases/offers",
    name: "partner-offers",
    component: () => import("./pages/PartnerOffersPage.vue"),
  },
];

