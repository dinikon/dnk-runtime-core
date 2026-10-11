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
    component: () => import("./ui/page/CatalogItemEditorPage.vue"),
  },
  {
    path: "catalog/items/:rootId/variants/:itemId",
    component: () => import("./ui/page/CatalogItemEditorPage.vue"),
  },
  {
    path: "catalog/categories",
    component: () => import("./ui/page/CategoryTreePage.vue"),
  },
  ...(["categories", "tags"] as const).flatMap((kind) => [
    {
      path: `catalog/${kind}/new`,
      component: () => import("./ui/page/ClassificationEditorPage.vue"),
      props: { category: kind === "categories" },
    },
    {
      path: `catalog/${kind}/:classificationId`,
      component: () => import("./ui/page/ClassificationEditorPage.vue"),
      props: { category: kind === "categories" },
    },
  ]),
  ...(["attributes", "tags"] as const).map((kind) => ({
    path: `catalog/${kind}`,
    component: () => import("./ui/page/CatalogCollectionPage.vue"),
    props: { kind },
  })),
  {
    path: "catalog/attributes/new",
    component: () => import("./ui/page/AttributeEditorPage.vue"),
  },
  {
    path: "catalog/attributes/:attributeId",
    component: () => import("./ui/page/AttributeEditorPage.vue"),
  },
];
