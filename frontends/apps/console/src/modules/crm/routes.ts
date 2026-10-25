import type { RouteRecordRaw } from "vue-router";

export const crmRoutes: RouteRecordRaw[] = [
  {
    path: "crm",
    component: () => import("./pages/CrmWorkspacePage.vue"),
    children: [
      {
        path: "leads",
        name: "crm-leads",
        component: () => import("./pages/SalesCollectionPage.vue"),
        props: { kind: "leads" },
      },
      {
        path: "deals",
        name: "crm-deals",
        component: () => import("./pages/SalesCollectionPage.vue"),
        props: { kind: "deals" },
      },
      {
        path: "leads/:id",
        name: "crm-lead-detail",
        component: () => import("./pages/SaleDetailPage.vue"),
        props: (route) => ({ kind: "leads", id: route.params.id }),
      },
      {
        path: "deals/:id",
        name: "crm-deal-detail",
        component: () => import("./pages/SaleDetailPage.vue"),
        props: (route) => ({ kind: "deals", id: route.params.id }),
      },
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
