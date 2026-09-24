<script setup lang="ts">
import type { SidebarProps } from "@/components/ui/sidebar";
import { ArrowLeft } from "@lucide/vue";
import { watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { adminNavigation } from "@/app/navigation";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
  useSidebar,
} from "@/components/ui/sidebar";
import ConsoleNavUser from "@/layouts/shared/ConsoleNavUser.vue";
import TenantWorkspaceMenu from "@/layouts/shared/TenantWorkspaceMenu.vue";
import AdminNav from "./AdminNav.vue";

const props = withDefaults(defineProps<SidebarProps>(), {
  variant: "inset",
});
const route = useRoute();
const { isMobile, setOpenMobile } = useSidebar();

watch(() => route.fullPath, () => {
  if (isMobile.value) setOpenMobile(false);
});
</script>

<template>
  <Sidebar v-bind="props">
    <SidebarHeader class="gap-2">
      <TenantWorkspaceMenu area="admin" />
      <SidebarSeparator />
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton as-child>
            <RouterLink to="/dashboard">
              <ArrowLeft />
              <span>Вернуться в CRM</span>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarHeader>
    <SidebarContent>
      <AdminNav :groups="adminNavigation" />
    </SidebarContent>
    <SidebarFooter>
      <ConsoleNavUser />
    </SidebarFooter>
  </Sidebar>
</template>
