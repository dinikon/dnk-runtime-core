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
    path: "channels/:channelId",
    name: "channel",
    component: () => import("./pages/ChannelPage.vue"),
    redirect: (to) => `/channels/${String(to.params.channelId)}/publications`,
    children: [
      {
        path: "publications",
        name: "channel-publications",
        component: () => import("./pages/ChannelPublicationsPage.vue"),
      },
      {
        path: "publications/:publicationId",
        name: "channel-publication",
        component: () => import("./pages/ChannelPublicationPage.vue"),
      },
      {
        path: "settings",
        name: "channel-settings",
        component: () => import("./pages/ChannelSettingsPage.vue"),
      },
    ],
  },
];
