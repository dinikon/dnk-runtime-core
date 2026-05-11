<script setup lang="ts">
import {
  AtSign,
  BadgeDollarSign,
  Bell,
  Boxes,
  CalendarDays,
  Code2,
  Database,
  Globe2,
  HelpCircle,
  KeyRound,
  LockKeyhole,
  LogOut,
  Mail,
  MonitorCog,
  Rocket,
  Server,
  Settings,
  Sparkles,
  UserCircle,
  Users,
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
  nested?: boolean;
}

defineProps<{
  title: string;
  breadcrumbs: BreadcrumbItemProps[];
  activeItem: string;
}>();

const userItems: SettingsNavigationItem[] = [
  {id: "profile", label: "Profile", to: "/settings/profile", icon: UserCircle},
  {id: "experience", label: "Experience", to: "/settings/experience", icon: MonitorCog},
  {id: "accounts", label: "Accounts", to: "/settings/accounts", icon: AtSign},
  {id: "emails", label: "Emails", to: "/settings/accounts/emails", icon: Mail, nested: true},
  {id: "calendar", label: "Calendar", to: "/settings/accounts/calendar", icon: CalendarDays, nested: true}
];

const workspaceItems: SettingsNavigationItem[] = [
  {id: "workspace-general", label: "General", to: "/settings/workspace/general", icon: Settings},
  {id: "data-model", label: "Data Model", to: "/settings/workspace/data-model", icon: Database},
  {id: "members", label: "Members", to: "/settings/workspace/members", icon: Users},
  {id: "roles", label: "Roles", to: "/settings/workspace/roles", icon: LockKeyhole},
  {id: "domains", label: "Domains", to: "/settings/workspace/domains", icon: Globe2},
  {id: "billing", label: "Billing", to: "/settings/workspace/billing", icon: BadgeDollarSign},
  {id: "apis-webhooks", label: "APIs & Webhooks", to: "/settings/workspace/apis-webhooks", icon: Code2},
  {id: "apps", label: "Apps", to: "/settings/workspace/apps", icon: Boxes},
  {id: "ai", label: "AI", to: "/settings/workspace/ai", icon: Sparkles},
  {id: "security", label: "Security", to: "/settings/workspace/security", icon: KeyRound}
];

const otherItems: SettingsNavigationItem[] = [
  {id: "admin-panel", label: "Admin Panel", to: "/settings/admin-panel", icon: Server},
  {id: "updates", label: "Updates", to: "/settings/updates", icon: Rocket},
  {id: "support", label: "Support", to: "/settings/support", icon: Bell},
  {id: "documentation", label: "Documentation", to: "/settings/documentation", icon: HelpCircle},
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
                  :class="item.nested ? 'pl-6' : undefined"
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
