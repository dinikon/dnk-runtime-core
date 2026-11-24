import type { RouteRecordRaw } from "vue-router";
export const feedBuilderRoutes: RouteRecordRaw[] = [
  {
    path: "feed-builder/feeds/:id/export",
    name: "feed-export",
    component: () => import("./pages/FeedExportPage.vue"),
  },
  {
    path: "feed-builder/feeds/:id/preview",
    name: "feed-preview",
    component: () => import("./pages/FeedPreviewPage.vue"),
  },
  {
    path: "feed-builder/feeds/:id/publications",
    name: "feed-publications",
    component: () => import("./pages/FeedPublicationsPage.vue"),
  },
  {
    path: "feed-builder/feeds",
    name: "feeds",
    component: () => import("./pages/FeedsPage.vue"),
  },
  {
    path: "feed-builder/feeds/new",
    name: "feed-new",
    component: () => import("./pages/FeedEditorPage.vue"),
  },
  {
    path: "feed-builder/feeds/:id",
    name: "feed-detail",
    component: () => import("./pages/FeedEditorPage.vue"),
  },
  {
    path: "feed-builder/feeds/:id/schema",
    name: "feed-schema",
    component: () => import("./pages/FeedSchemaPage.vue"),
  },
];
