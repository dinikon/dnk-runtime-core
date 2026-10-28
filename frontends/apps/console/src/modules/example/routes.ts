import type { RouteRecordRaw } from "vue-router";
import { headerExamples } from "./model/header-example.constants";

export const exampleRoutes: RouteRecordRaw[] = import.meta.env.DEV
  ? [
      {
        path: "",
        name: "example",
        redirect: { name: "example-empty-state" },
      },
      {
        path: "empty-state",
        name: "example-empty-state",
        components: {
          default: () => import("./pages/EmptyStatePage.vue"),
          header: () => import("./ui/EmptyStateHeader.vue"),
        },
      },
      {
        path: "headers",
        redirect: { name: "example-header-2" },
      },
      ...headerExamples.map((example) => ({
        path: `headers/${example.variant}`,
        name: `example-header-${example.number}`,
        components: {
          default: () => import("./pages/HeaderExamplePage.vue"),
          header: () => import("./ui/headers/HeaderExampleHeader.vue"),
        },
        props: {
          default: { variant: example.variant },
          header: { title: `Header ${example.number}` },
        },
      })),
    ]
  : [];
