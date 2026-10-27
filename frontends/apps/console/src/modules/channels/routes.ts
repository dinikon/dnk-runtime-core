import type { RouteRecordRaw } from "vue-router";
export const channelRoutes: RouteRecordRaw[] = [
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
