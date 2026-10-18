import type { RouteRecordRaw } from "vue-router";
export const channelsRoutes: RouteRecordRaw[] = [
  {
    path: "channels",
    component: () => import("./pages/ChannelsWorkspacePage.vue"),
    children: [
      {
        path: "",
        name: "channels-list",
        component: () => import("./pages/ChannelsPage.vue"),
      },
      {
        path: ":channelId",
        name: "channel-detail",
        component: () => import("./pages/ChannelPage.vue"),
      },
    ],
  },
];
