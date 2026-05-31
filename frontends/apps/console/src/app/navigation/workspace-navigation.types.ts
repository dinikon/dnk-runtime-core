import type { Component } from "vue";

export interface WorkspaceNavigationBrand {
  name: string;
  description: string;
  url: string;
  icon: Component;
}

export interface WorkspaceNavigationSubItem {
  title: string;
  url: string;
}

export interface WorkspaceNavigationMainItem {
  title: string;
  url: string;
  icon: Component;
  isActive?: boolean;
  items?: WorkspaceNavigationSubItem[];
}

export interface WorkspaceNavigationLink {
  title: string;
  url: string;
  icon: Component;
}

export interface WorkspaceNavigationProject {
  name: string;
  url: string;
  icon: Component;
}

export interface WorkspaceNavigation {
  brand: WorkspaceNavigationBrand;
  navMain: WorkspaceNavigationMainItem[];
  navSecondary: WorkspaceNavigationLink[];
  projects: WorkspaceNavigationProject[];
}
