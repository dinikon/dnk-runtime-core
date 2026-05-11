<script setup lang="ts">
import {
  Database,
  FileText,
  LogOut,
  MessagesSquare,
  PlugZap,
  UserCircle,
  X
} from "lucide-vue-next";
import {RouterLink} from "vue-router";

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {Card, CardContent} from "@/components/ui/card";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
} from "@/components/ui/sidebar";

interface BreadcrumbItemProps {
  label: string;
  to?: string;
}

interface SettingsNavigationItem {
  id: string;
  label: string;
  to: string;
  icon: typeof UserCircle;
}

defineProps<{
  title: string;
  breadcrumbs: BreadcrumbItemProps[];
  activeItem: string;
}>();

const userItems: SettingsNavigationItem[] = [
  {id: "profile", label: "Profile", to: "/settings/profile", icon: UserCircle}
];

const workspaceItems: SettingsNavigationItem[] = [
  {id: "data-model", label: "Data Model", to: "/settings/workspace/data-model", icon: Database},
  {id: "communication-providers", label: "Providers", to: "/settings/workspace/communication/providers", icon: PlugZap},
  {
    id: "communication-templates",
    label: "Templates",
    to: "/settings/workspace/communication/templates",
    icon: FileText
  },
  {
    id: "communication-messages",
    label: "Messages",
    to: "/settings/workspace/communication/messages",
    icon: MessagesSquare
  }
];

const otherItems: SettingsNavigationItem[] = [
  {id: "logout", label: "Log out", to: "/login", icon: LogOut}
];

const navigationGroups = [
  {label: "User", items: userItems},
  {label: "Workspace", items: workspaceItems},
  {label: "Other", items: otherItems}
];
</script>

<template>
  <SidebarProvider class="h-svh max-h-svh overflow-hidden">
    <Sidebar variant="inset">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" as-child>
              <RouterLink to="/">
                <div
                    class="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
                >
                  <X class="size-4"/>
                </div>
                <div class="grid flex-1 text-left text-sm leading-tight">
                  <span class="truncate font-medium">Exit Settings</span>
                  <span class="truncate text-xs">Back to console</span>
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
            <SidebarMenuItem v-for="item in group.items" :key="item.id">
              <SidebarMenuButton
                  as-child
                  :is-active="activeItem === item.id"
                  :tooltip="item.label"
              >
                <RouterLink :to="item.to">
                  <component :is="item.icon"/>
                  <span>{{ item.label }}</span>
                </RouterLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>

    <SidebarInset class="min-h-0 overflow-hidden">
      <div class="flex min-h-0 flex-1 flex-col gap-4 p-4">
        <header class="flex h-8 shrink-0 items-center">
          <Breadcrumb>
            <BreadcrumbList>
              <template v-for="(breadcrumb, index) in breadcrumbs" :key="`${breadcrumb.label}-${index}`">
                <BreadcrumbItem>
                  <BreadcrumbLink v-if="breadcrumb.to" as-child>
                    <RouterLink :to="breadcrumb.to">
                      {{ breadcrumb.label }}
                    </RouterLink>
                  </BreadcrumbLink>
                  <BreadcrumbPage v-else>
                    {{ breadcrumb.label }}
                  </BreadcrumbPage>
                </BreadcrumbItem>
                <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1"/>
              </template>
            </BreadcrumbList>
          </Breadcrumb>
        </header>

        <Card class="min-h-0 flex-1 overflow-hidden py-0">
          <CardContent class="min-h-0 flex-1 overflow-auto p-8">
            <slot>
              <div class="text-sm text-muted-foreground">{{ title }}</div>
            </slot>
          </CardContent>
        </Card>
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>
