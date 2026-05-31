<script setup lang="ts">
import type { SidebarProps } from "@/components/ui/sidebar";
import { RouterLink } from "vue-router";

import { getWorkspaceNavigationMock } from "@/app/navigation";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import WorkspaceNavMain from "./WorkspaceNavMain.vue";
import WorkspaceNavProjects from "./WorkspaceNavProjects.vue";
import WorkspaceNavSecondary from "./WorkspaceNavSecondary.vue";
import WorkspaceNavUser from "./WorkspaceNavUser.vue";

const props = withDefaults(defineProps<SidebarProps>(), {
  variant: "inset",
  collapsible: "icon",
});

const navigation = getWorkspaceNavigationMock();
</script>

<template>
  <Sidebar v-bind="props">
    <SidebarHeader>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton size="lg" as-child>
            <RouterLink :to="navigation.brand.url">
              <div
                class="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
              >
                <component :is="navigation.brand.icon" class="size-4" />
              </div>
              <div class="grid flex-1 text-left text-sm leading-tight">
                <span class="truncate font-medium">
                  {{ navigation.brand.name }}
                </span>
                <span class="truncate text-xs">
                  {{ navigation.brand.description }}
                </span>
              </div>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarHeader>

    <SidebarContent>
      <WorkspaceNavMain :items="navigation.navMain" />
      <WorkspaceNavProjects :projects="navigation.projects" />
      <WorkspaceNavSecondary :items="navigation.navSecondary" class="mt-auto" />
    </SidebarContent>

    <SidebarFooter>
      <WorkspaceNavUser />
    </SidebarFooter>
    <SidebarRail />
  </Sidebar>
</template>
