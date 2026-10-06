import type { RouteRecordRaw } from "vue-router";
export const catalogRoutes: RouteRecordRaw[] = [
  { path: "catalog/content-blocks", name: "catalog-content-blocks", component: () => import("./pages/ContentBlocksPage.vue") },
  { path: "catalog/product-types", name: "catalog-product-types", component: () => import("./pages/ProductTypesPage.vue") },
  {
    path: "catalog/categories",
    name: "catalog-categories",
    component: () => import("./pages/CategoriesPage.vue"),
  },
  {
    path: "catalog/categories/new",
    name: "catalog-category-new",
    component: () => import("./pages/CreateCategoryPage.vue"),
  },
  {
    path: "catalog/categories/:categoryId",
    name: "catalog-category",
    component: () => import("./pages/CategoryPage.vue"),
  },
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
