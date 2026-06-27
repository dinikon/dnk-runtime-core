<script setup lang="ts">
import type { SidebarProps } from "@/components/ui/sidebar";

import { Command } from "@lucide/vue";
import { RouterLink } from "vue-router";

import { workspaceNavigation } from "@/app/navigation";
import WorkspaceNavMain from "./WorkspaceNavMain.vue";
import WorkspaceNavSecondary from "./WorkspaceNavSecondary.vue";
import WorkspaceNavUser from "./WorkspaceNavUser.vue";
import WorkspaceTenantInfo from "./WorkspaceTenantInfo.vue";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const props = withDefaults(defineProps<SidebarProps>(), {
  variant: "inset",
});
</script>

<template>
  <Sidebar v-bind="props">
    <SidebarHeader>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton size="lg" as-child>
            <RouterLink to="/dashboard">
              <div
                class="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground"
              >
                <Command class="size-4" />
              </div>
              <WorkspaceTenantInfo />
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarHeader>
    <SidebarContent>
      <WorkspaceNavMain :groups="workspaceNavigation.navGroups" />
      <WorkspaceNavSecondary
        :items="[workspaceNavigation.support]"
        class="mt-auto"
      />
    </SidebarContent>
    <SidebarFooter>
      <WorkspaceNavUser />
    </SidebarFooter>
  </Sidebar>
</template>
