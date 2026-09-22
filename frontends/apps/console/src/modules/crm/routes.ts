import type { RouteRecordRaw } from "vue-router";

export const crmRoutes: RouteRecordRaw[] = [
  {
    path: "crm/contacts",
    name: "crm-contacts",
    component: () => import("./pages/ContactsPage.vue"),
  },
  {
    path: "crm/companies",
    name: "crm-companies",
    component: () => import("./pages/CompaniesPage.vue"),
  },
];
