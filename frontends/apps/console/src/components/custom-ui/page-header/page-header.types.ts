import type { Component } from "vue";
import type { ButtonVariants } from "@/components/ui/button";

export interface PageHeaderAction {
  id: string;
  label: string;
  variant?: ButtonVariants["variant"];
  icon?: Component;
  mobileOrder?: number;
  disabled?: boolean;
}

export interface PageHeaderBreadcrumb {
  id: string;
  label: string;
}

export interface PageHeaderTab {
  value: string;
  label: string;
}
