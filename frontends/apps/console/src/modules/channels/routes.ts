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
        path: ":channelId/publications/:publicationId/import/:preparationId",
        name: "channel-publication-import",
        component: () => import("./pages/PublicationImportPage.vue"),
      },
      {
        path: ":channelId/content-updates/:runId",
        name: "channel-content-update",
        component: () => import("./pages/ContentUpdatePage.vue"),
      },
      {
        path: ":channelId",
        name: "channel-detail",
        component: () => import("./pages/ChannelPage.vue"),
      },
    ],
  },
];
