import type { RouteRecordRaw } from "vue-router";
export const channelRoutes: RouteRecordRaw[] = [
  {
    path: "channels/:id/publications",
    name: "channel-publications",
    redirect: (to) => ({
      name: "channel-detail",
      params: { id: to.params.id },
      query: to.query,
      hash: to.hash,
    }),
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
    component: () => import("./pages/ChannelDetailsPage.vue"),
  },
];
