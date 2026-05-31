import type { RouteRecordRaw } from "vue-router";

import ContactsHeader from "@/modules/crm/components/ContactsHeader.vue";
import ContactsPage from "@/modules/crm/pages/ContactsPage.vue";

export const crmRoutes: RouteRecordRaw[] = [
  {
    path: "crm/contacts",
    name: "crm-contacts",
    components: {
      default: ContactsPage,
      header: ContactsHeader,
    },
  },
];
