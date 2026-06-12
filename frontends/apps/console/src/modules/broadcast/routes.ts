import type { RouteRecordRaw } from "vue-router";

import BroadcastHeader from "@/modules/broadcast/components/BroadcastHeader.vue";
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
];
