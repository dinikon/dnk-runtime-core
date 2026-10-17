import type { RouteRecordRaw } from "vue-router";

export const crmRoutes: RouteRecordRaw[] = [
  {
    path: "crm",
    component: () => import("./pages/CrmWorkspacePage.vue"),
    children: [
      { path: "", redirect: { name: "crm-contacts" } },
      {
        path: "contacts",
        name: "crm-contacts",
        component: () => import("./pages/ContactsPage.vue"),
      },
      {
        path: "contacts/:id",
        name: "crm-contact-detail",
        component: () => import("./pages/CrmDetailPage.vue"),
        props: (route) => ({ kind: "contacts", id: route.params.id }),
      },
      {
        path: "companies",
        name: "crm-companies",
        component: () => import("./pages/CompaniesPage.vue"),
      },
      {
        path: "companies/:id",
        name: "crm-company-detail",
        component: () => import("./pages/CrmDetailPage.vue"),
        props: (route) => ({ kind: "companies", id: route.params.id }),
      },
    ],
  },
];
