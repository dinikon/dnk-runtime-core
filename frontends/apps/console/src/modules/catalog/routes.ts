import type { RouteRecordRaw } from "vue-router";
export const catalogRoutes: RouteRecordRaw[] = [
  {
    path: "catalog/products",
    name: "catalog-products",
    component: () => import("./pages/ProductsPage.vue"),
  },
  {
    path: "catalog/products/new",
    name: "catalog-product-new",
    component: () => import("./pages/CreateProductPage.vue"),
  },
  {
    path: "catalog/products/:productId",
    name: "catalog-product",
    component: () => import("./pages/ProductPage.vue"),
  },
];
