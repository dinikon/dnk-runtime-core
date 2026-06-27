import type { RouteRecordRaw } from "vue-router";

import CompaniesHeader from "@/modules/crm/components/CompaniesHeader.vue";
import CompaniesPage from "@/modules/crm/pages/CompaniesPage.vue";
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
  {
    path: "crm/companies",
    name: "crm-companies",
    components: {
      default: CompaniesPage,
      header: CompaniesHeader,
    },
  },
];
