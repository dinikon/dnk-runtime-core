<script setup lang="ts">
import type { SidebarProps } from "@/components/ui/sidebar";

import { workspaceNavigation } from "@/app/navigation";
import ConsoleNavUser from "@/layouts/shared/ConsoleNavUser.vue";
import TenantWorkspaceMenu from "@/layouts/shared/TenantWorkspaceMenu.vue";
import WorkspaceNavMain from "./WorkspaceNavMain.vue";
import WorkspaceNavSecondary from "./WorkspaceNavSecondary.vue";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar";

const props = withDefaults(defineProps<SidebarProps>(), {
  variant: "inset",
});
</script>

<template>
  <Sidebar v-bind="props">
    <SidebarHeader>
      <TenantWorkspaceMenu area="workspace" />
    </SidebarHeader>
    <SidebarContent>
      <WorkspaceNavMain :groups="workspaceNavigation.navGroups" />
      <WorkspaceNavSecondary
        :items="[workspaceNavigation.support]"
        class="mt-auto"
      />
    </SidebarContent>
    <SidebarFooter>
      <ConsoleNavUser />
    </SidebarFooter>
  </Sidebar>
</template>
