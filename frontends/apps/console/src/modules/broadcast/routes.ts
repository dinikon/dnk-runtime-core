import type { RouteRecordRaw } from "vue-router";

import BroadcastHeader from "@/modules/broadcast/components/BroadcastHeader.vue";
import BroadcastDetailsPage from "@/modules/broadcast/pages/BroadcastDetailsPage.vue";
import BroadcastsPage from "@/modules/broadcast/pages/BroadcastsPage.vue";

export const broadcastRoutes: RouteRecordRaw[] = [
  {
    path: "cdp/broadcasts",
    name: "broadcasts",
    components: {
      default: BroadcastsPage,
      header: BroadcastHeader,
    },
    meta: {
      title: "Broadcasts",
    },
  },
  {
    path: "cdp/broadcasts/:id",
    name: "broadcast-detail",
    components: {
      default: BroadcastDetailsPage,
      header: BroadcastHeader,
    },
    meta: {
      title: "Broadcast detail",
    },
  },
];
