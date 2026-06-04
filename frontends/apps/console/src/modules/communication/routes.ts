import type { RouteRecordRaw } from "vue-router";

import CommunicationHeader from "@/modules/communication/components/CommunicationHeader.vue";
import DeliveriesPage from "@/modules/communication/pages/DeliveriesPage.vue";
import ProvidersPage from "@/modules/communication/pages/ProvidersPage.vue";
import TemplatesPage from "@/modules/communication/pages/TemplatesPage.vue";

export const communicationRoutes: RouteRecordRaw[] = [
  {
    path: "cdp/providers",
    name: "communication-providers",
    components: {
      default: ProvidersPage,
      header: CommunicationHeader,
    },
    meta: {
      title: "Providers",
    },
  },
  {
    path: "cdp/templates",
    name: "communication-templates",
    components: {
      default: TemplatesPage,
      header: CommunicationHeader,
    },
    meta: {
      title: "Templates",
    },
  },
  {
    path: "cdp/deliveries",
    name: "communication-deliveries",
    components: {
      default: DeliveriesPage,
      header: CommunicationHeader,
    },
    meta: {
      title: "Deliveries",
    },
  },
  {
    path: "cdp/delivery",
    redirect: { name: "communication-deliveries" },
  },
];
