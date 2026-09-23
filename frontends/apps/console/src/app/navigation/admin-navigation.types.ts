import type { Component } from "vue";

export interface AdminNavigationItem {
  title: string;
  icon?: Component;
  url?: string;
  disabled?: boolean;
  hidden?: boolean;
  defaultOpen?: boolean;
  requiredRole?: "admin";
  items?: AdminNavigationItem[];
}

export interface AdminNavigationGroup {
  title: string;
  hidden?: boolean;
  items: AdminNavigationItem[];
}
