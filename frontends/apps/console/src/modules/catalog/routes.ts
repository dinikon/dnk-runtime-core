import type { RouteRecordRaw } from "vue-router";
export const catalogRoutes: RouteRecordRaw[] = [
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
  {
    path: "catalog/attributes/new",
    component: () => import("./ui/page/AttributeEditorPage.vue"),
  },
  {
    path: "catalog/attributes/:attributeId",
    component: () => import("./ui/page/AttributeEditorPage.vue"),
  },
  { path: "catalog", redirect: "/catalog/products" },
  ...(
    [
      "products",
      "product-types",
      "content-blocks",
      "attributes",
      "tags",
    ] as const
  ).map((kind) => ({
    path: `catalog/${kind}`,
    name: `catalog-${kind}`,
    component: () => import("./ui/page/CatalogCollectionPage.vue"),
    props: { kind },
  })),
  {
    path: "catalog/products/new",
    name: "catalog-product-new",
    component: () => import("./ui/page/ProductCreatePage.vue"),
  },
  {
    path: "catalog/products/:productId",
    name: "catalog-product",
    component: () => import("./ui/page/ProductEditorPage.vue"),
  },
  {
    path: "catalog/products/:productId/variants/:variantId",
    name: "catalog-variant",
    component: () => import("./ui/page/ProductEditorPage.vue"),
  },
  ...(["product-types", "content-blocks"] as const).flatMap((kind) => [
    {
      path: `catalog/${kind}/new`,
      component: () => import("./ui/page/DefinitionEditorPage.vue"),
      props: { block: kind === "content-blocks" },
    },
    {
      path: `catalog/${kind}/:definitionId`,
      component: () => import("./ui/page/DefinitionEditorPage.vue"),
      props: { block: kind === "content-blocks" },
    },
  ]),
];
