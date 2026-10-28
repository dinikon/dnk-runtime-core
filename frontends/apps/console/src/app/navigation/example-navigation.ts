import { Inbox, PanelTop } from "@lucide/vue";
import type { Component } from "vue";

export interface ExampleNavigationItem {
  title: string;
  url: string;
  icon: Component;
}

export interface ExampleNavigationGroup {
  title: string;
  items: readonly ExampleNavigationItem[];
}

export const exampleNavigation: readonly ExampleNavigationGroup[] = [
  {
    title: "Example",
    items: [{ title: "EmptyState", url: "/example/empty-state", icon: Inbox }],
  },
  {
    title: "Headers",
    items: [
      {
        title: "Header 2 · Breadcrumbs",
        url: "/example/headers/breadcrumbs",
        icon: PanelTop,
      },
      {
        title: "Header 3 · Tabs above",
        url: "/example/headers/tabs-top",
        icon: PanelTop,
      },
      {
        title: "Header 4 · Search",
        url: "/example/headers/search",
        icon: PanelTop,
      },
      {
        title: "Header 5 · Compact",
        url: "/example/headers/compact",
        icon: PanelTop,
      },
      {
        title: "Header 6 · Profile",
        url: "/example/headers/profile",
        icon: PanelTop,
      },
      {
        title: "Header 7 · Tabs below",
        url: "/example/headers/tabs-bottom",
        icon: PanelTop,
      },
      {
        title: "Header 8 · Search & avatar",
        url: "/example/headers/search-avatar",
        icon: PanelTop,
      },
    ],
  },
];
