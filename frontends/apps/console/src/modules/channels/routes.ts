import type { RouteRecordRaw } from "vue-router";
export const channelRoutes: RouteRecordRaw[] = [
  {
    path: "channels/:id/publications",
    name: "channel-publications",
    component: () => import("./pages/ChannelPublicationsPage.vue"),
  },
  {
    path: "channels/:id/publications/:publicationId",
    name: "channel-publication",
    component: () => import("./pages/ChannelPublicationPage.vue"),
  },
  {
    path: "channels",
    name: "channels",
    component: () => import("./pages/ChannelsPage.vue"),
  },
  {
    path: "channels/new",
    name: "channel-new",
    component: () => import("./pages/ChannelEditorPage.vue"),
  },
  {
    path: "channels/:id",
    name: "channel-detail",
    component: () => import("./pages/ChannelEditorPage.vue"),
  },
];
