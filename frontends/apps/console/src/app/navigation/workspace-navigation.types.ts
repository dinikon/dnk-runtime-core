import type { Component } from "vue";

export interface WorkspaceNavigationItem {
  title: string;
  url: string;
  icon: Component;
  external?: boolean;
  defaultOpen?: boolean;
  items?: WorkspaceNavigationSubItem[];
}

export interface WorkspaceNavigationSubItem {
  title: string;
  url: string;
  external?: boolean;
}

export interface WorkspaceNavigationGroup {
  title: string;
  items: WorkspaceNavigationItem[];
}

export interface WorkspaceNavigation {
  navGroups: WorkspaceNavigationGroup[];
  support: WorkspaceNavigationItem;
}
