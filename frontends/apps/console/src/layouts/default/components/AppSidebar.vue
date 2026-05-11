<script setup lang="ts">
import type {LucideIcon} from "lucide-vue-next";
import type {SidebarProps} from "@/components/ui/sidebar";

import {
  BookOpen,
  CheckSquare,
  Command,
  ContactRound,
  Database,
  FileText,
  Settings,
  Store,
  Target,
  Workflow
} from "lucide-vue-next";
import {RouterLink, useRoute} from "vue-router";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

interface NavigationItem {
  label: string;
  icon: LucideIcon;
  to?: string;
}

const props = withDefaults(defineProps<SidebarProps>(), {
  variant: "inset",
});

const route = useRoute();

const workspaceItems: NavigationItem[] = [
  {label: "Objects", icon: Database, to: "/"},
  {label: "Contacts", icon: ContactRound},
  {label: "Tasks", icon: CheckSquare},
  {label: "Notes", icon: FileText},
  {label: "Opportunities", icon: Target},
  {label: "Workflows", icon: Workflow}
];

const otherItems: NavigationItem[] = [
  {label: "Settings", icon: Settings, to: "/settings/profile"},
  {label: "Documentation", icon: BookOpen},
  {label: "App store", icon: Store}
];

const navigationGroups = [
  {label: "Workspace", items: workspaceItems},
  {label: "Other", items: otherItems}
];

function isActive(to?: string): boolean {
  if (!to) {
    return false;
  }

  if (to === "/") {
    return route.path === "/";
  }

  return route.path.startsWith(to);
}
</script>

<template>
  <Sidebar v-bind="props">
    <SidebarHeader>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton size="lg" as-child>
            <RouterLink to="/">
              <div
                  class="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
              >
                <Command class="size-4"/>
              </div>
              <div class="grid flex-1 text-left text-sm leading-tight">
                <span class="truncate font-medium">dNiko</span>
                <span class="truncate text-xs">Console</span>
              </div>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarHeader>

    <SidebarContent>
      <SidebarGroup v-for="group in navigationGroups" :key="group.label">
        <SidebarGroupLabel>{{ group.label }}</SidebarGroupLabel>
        <SidebarMenu>
          <SidebarMenuItem v-for="item in group.items" :key="item.label">
            <SidebarMenuButton
                v-if="item.to"
                as-child
                :tooltip="item.label"
                :is-active="isActive(item.to)"
            >
              <RouterLink :to="item.to">
                <component :is="item.icon"/>
                <span>{{ item.label }}</span>
              </RouterLink>
            </SidebarMenuButton>

            <SidebarMenuButton
                v-else
                :tooltip="item.label"
                disabled
                class="disabled:opacity-60"
            >
              <component :is="item.icon"/>
              <span>{{ item.label }}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarGroup>
    </SidebarContent>
  </Sidebar>
</template>
